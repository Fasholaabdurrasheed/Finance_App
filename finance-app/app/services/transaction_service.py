from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class TransactionService:
    def __init__(self, db: Session):
        self.db = db

    def list_transactions(
        self,
        user_id: int,
        start_date: date | None,
        end_date: date | None,
        category_id: int | None,
        tx_type: TransactionType | None,
    ) -> list[Transaction]:
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if tx_type:
            query = query.filter(Transaction.type == tx_type)

        return query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()

    def create(self, user_id: int, payload: TransactionCreate) -> Transaction:
        self._validate_category_ownership(user_id, payload.category_id)

        tx = Transaction(
            user_id=user_id,
            category_id=payload.category_id,
            amount=payload.amount,
            type=payload.type,
            description=payload.description,
            transaction_date=payload.transaction_date,
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx

    def update(self, user_id: int, tx_id: int, payload: TransactionUpdate) -> Transaction:
        tx = self._get_owned_transaction(user_id, tx_id)

        if payload.category_id is not None:
            self._validate_category_ownership(user_id, payload.category_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(tx, field, value)

        self.db.commit()
        self.db.refresh(tx)
        return tx

    def delete(self, user_id: int, tx_id: int) -> None:
        tx = self._get_owned_transaction(user_id, tx_id)
        self.db.delete(tx)
        self.db.commit()

    def _get_owned_transaction(self, user_id: int, tx_id: int) -> Transaction:
        tx = (
            self.db.query(Transaction)
            .filter(Transaction.id == tx_id, Transaction.user_id == user_id)
            .first()
        )
        if not tx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        return tx

    def _validate_category_ownership(self, user_id: int, category_id: int | None) -> None:
        if category_id is None:
            return

        category = self.db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        if category.owner_id not in (None, user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Category is not accessible")
