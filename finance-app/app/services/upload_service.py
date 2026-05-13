from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO, StringIO
from typing import Any

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.upload import ExcelUploadPreview, ExcelUploadResponse, UploadValidationError
from app.utils.excel_utils import (
    clean_text,
    infer_transaction_type_from_amount,
    normalize_amount,
    normalize_transaction_type,
    parse_decimal,
    resolve_columns,
    row_signature,
)
from app.utils.logger import get_logger

logger = get_logger("app.services.upload_service")


@dataclass(slots=True)
class NormalizedTransactionRow:
    transaction_date: date
    amount: Any
    transaction_type: TransactionType
    description: str | None
    category_name: str | None


class ExcelUploadService:
    def __init__(self, db: Session):
        self.db = db

    def preview(self, file_name: str, file_bytes: bytes) -> ExcelUploadPreview:
        dataframe = self._load_dataframe(file_name, file_bytes)
        normalized_rows, validation_errors, detected_columns = self._normalize_dataframe(dataframe)
        return ExcelUploadPreview(
            total_rows=len(dataframe),
            valid_rows=len(normalized_rows),
            duplicate_rows=0,
            invalid_rows=len(validation_errors),
            detected_columns=detected_columns,
            validation_errors=validation_errors,
        )

    def process(self, user: User, file_name: str, file_bytes: bytes, upload_id: int | None = None) -> ExcelUploadResponse:
        dataframe = self._load_dataframe(file_name, file_bytes)
        normalized_rows, validation_errors, _ = self._normalize_dataframe(dataframe)

        if validation_errors and not normalized_rows:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Excel file contains no valid transaction rows", "errors": [error.model_dump() for error in validation_errors]},
            )

        existing_signatures = self._existing_transaction_signatures(user.id)
        seen_signatures: set[tuple[Any, ...]] = set()
        inserted = 0
        duplicates = 0
        created_categories = 0
        category_cache: dict[tuple[str, TransactionType], Category] = {}

        for normalized in normalized_rows:
            signature = row_signature(
                normalized.transaction_date,
                normalized.amount,
                normalized.transaction_type.value,
                normalized.description,
                normalized.category_name,
            )

            if signature in existing_signatures or signature in seen_signatures:
                duplicates += 1
                continue

            seen_signatures.add(signature)

            category_id = None
            if normalized.category_name:
                category, created = self._get_or_create_category(
                    user.id,
                    normalized.category_name,
                    normalized.transaction_type,
                    category_cache,
                )
                # attach upload provenance to created category when applicable
                if upload_id is not None and created:
                    category.upload_id = upload_id
                category_id = category.id
                created_categories += int(created)

            transaction = Transaction(
                user_id=user.id,
                category_id=category_id,
                type=normalized.transaction_type,
                amount=normalized.amount,
                description=normalized.description,
                transaction_date=normalized.transaction_date,
            )
            if upload_id is not None:
                transaction.upload_id = upload_id

            self.db.add(transaction)
            inserted += 1

        # Update upload stats if upload_id provided
        if upload_id is not None:
            try:
                from app.models.upload import Upload

                upload = self.db.query(Upload).filter(Upload.id == upload_id).first()
                if upload:
                    upload.status = "complete"
                    upload.processed_at = func.now()
                    upload.rows_total = len(dataframe)
                    upload.rows_inserted = inserted
                    self.db.add(upload)
            except Exception:
                # non-fatal; commit below will still persist created rows
                logger.exception("Failed to update upload record stats")

        self.db.commit()

        return ExcelUploadResponse(
            message="Excel file imported successfully",
            total_rows=len(dataframe),
            inserted_rows=inserted,
            duplicate_rows=duplicates,
            invalid_rows=len(validation_errors),
            created_categories=created_categories,
            file_name=file_name,
        )

    def _load_dataframe(self, file_name: str, file_bytes: bytes) -> pd.DataFrame:
        """
        Load DataFrame from Excel or CSV file.
        - Detects format by file extension
        - Normalizes column names
        - Removes completely empty rows
        - Raises HTTPException on invalid/empty files
        """
        file_lower = file_name.lower()
        
        try:
            if file_lower.endswith(".xlsx"):
                logger.debug(f"Loading Excel file: {file_name}")
                dataframe = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
            elif file_lower.endswith(".csv"):
                logger.debug(f"Loading CSV file: {file_name}")
                # Try UTF-8 first, fallback to latin-1
                try:
                    dataframe = pd.read_csv(StringIO(file_bytes.decode("utf-8")))
                except UnicodeDecodeError:
                    logger.debug(f"UTF-8 decode failed, trying latin-1: {file_name}")
                    dataframe = pd.read_csv(StringIO(file_bytes.decode("latin-1")))
            else:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported file format. Supported: .xlsx, .csv"
                )
        except HTTPException:
            raise
        except UnicodeDecodeError as exc:
            logger.error(f"File encoding error: {exc}, filename={file_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File encoding not supported (UTF-8 or Latin-1 expected)"
            ) from exc
        except Exception as exc:
            logger.error(f"Failed to parse file {file_name}: {exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to parse file: {str(exc)}"
            ) from exc

        if dataframe.empty:
            logger.warning(f"File is empty: {file_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty or contains no data rows"
            )

        # Normalize columns: strip whitespace
        dataframe.columns = [str(column).strip() for column in dataframe.columns]
        dataframe = dataframe.dropna(how="all")  # Drop completely empty rows
        
        logger.debug(f"Loaded {len(dataframe)} rows, {len(dataframe.columns)} columns from {file_name}")
        return dataframe

    def _normalize_dataframe(self, dataframe: pd.DataFrame) -> tuple[list[NormalizedTransactionRow], list[UploadValidationError], list[str]]:
        resolved = resolve_columns(list(dataframe.columns))
        detected_columns = [value for value in [resolved.date, resolved.amount, resolved.debit, resolved.credit, resolved.transaction_type, resolved.description, resolved.category] if value]

        logger.debug(f"File columns: {list(dataframe.columns)}")
        logger.debug(f"Resolved date: {resolved.date}, amount: {resolved.amount}, debit: {resolved.debit}, credit: {resolved.credit}")
        
        if not resolved.date:
            available_columns = list(dataframe.columns)
            error_detail = (
                f"Missing required date column. "
                f"File has columns: {available_columns}. "
                f"Expected one of: date, transaction_date, transaction date, txn date, posted date, value date, booking date, entry date"
            )
            logger.warning(f"Column detection failed: {error_detail}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_detail)
        if not (resolved.amount or (resolved.debit and resolved.credit)):
            available_columns = list(dataframe.columns)
            error_detail = (
                f"Missing required amount columns. "
                f"File has columns: {available_columns}. "
                f"Expected: 'amount' column OR both 'debit' and 'credit' columns"
            )
            logger.warning(f"Column detection failed: {error_detail}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_detail)

        normalized_rows: list[NormalizedTransactionRow] = []
        validation_errors: list[UploadValidationError] = []

        for index, row in dataframe.iterrows():
            row_number = int(index) + 2
            date_value = pd.to_datetime(row.get(resolved.date), errors="coerce")
            if pd.isna(date_value):
                validation_errors.append(UploadValidationError(row_number=row_number, message="Invalid or missing transaction date"))
                continue

            raw_amount = None
            if resolved.amount:
                raw_amount = parse_decimal(row.get(resolved.amount))
            elif resolved.debit and resolved.credit:
                debit_value = parse_decimal(row.get(resolved.debit))
                credit_value = parse_decimal(row.get(resolved.credit))
                if debit_value is not None and debit_value > 0:
                    raw_amount = -abs(debit_value)
                elif credit_value is not None and credit_value > 0:
                    raw_amount = abs(credit_value)

            if raw_amount is None:
                validation_errors.append(UploadValidationError(row_number=row_number, message="Invalid or missing amount"))
                continue

            inferred_type = normalize_transaction_type(row.get(resolved.transaction_type)) if resolved.transaction_type else None
            transaction_type_value = inferred_type or infer_transaction_type_from_amount(raw_amount)
            transaction_type = TransactionType.INCOME if transaction_type_value == "income" else TransactionType.EXPENSE

            normalized_rows.append(
                NormalizedTransactionRow(
                    transaction_date=date_value.date(),
                    amount=normalize_amount(raw_amount),
                    transaction_type=transaction_type,
                    description=clean_text(row.get(resolved.description)) if resolved.description else None,
                    category_name=clean_text(row.get(resolved.category)) if resolved.category else None,
                )
            )

        return normalized_rows, validation_errors, detected_columns

    def _existing_transaction_signatures(self, user_id: int) -> set[tuple[Any, ...]]:
        rows = (
            self.db.query(
                Transaction.transaction_date,
                Transaction.amount,
                Transaction.type,
                Transaction.description,
                Category.name.label("category_name"),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .filter(Transaction.user_id == user_id)
            .all()
        )
        return {
            row_signature(row.transaction_date, row.amount, row.type.value, row.description, row.category_name)
            for row in rows
        }

    def _get_or_create_category(
        self,
        user_id: int,
        category_name: str,
        transaction_type: TransactionType,
        cache: dict[tuple[str, TransactionType], Category],
    ) -> tuple[Category, bool]:
        key = (category_name.strip().lower(), transaction_type)
        cached = cache.get(key)
        if cached:
            return cached, False

        category = (
            self.db.query(Category)
            .filter(Category.owner_id == user_id, Category.name.ilike(category_name), Category.type == transaction_type)
            .first()
        )
        created = False
        if category is None:
            category = Category(owner_id=user_id, name=category_name, type=transaction_type)
            self.db.add(category)
            self.db.flush()
            created = True

        cache[key] = category
        return category, created