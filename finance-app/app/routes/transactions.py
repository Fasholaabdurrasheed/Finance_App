from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.transaction import (
    BulkTransactionCreateRequest,
    BulkTransactionCreateResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = None,
    tx_type: TransactionType | None = None,
    search: str | None = None,
    sort_by: str = "transaction_date",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TransactionResponse]:
    records = TransactionService(db).list_transactions(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        tx_type=tx_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return [_to_transaction_response(item) for item in records]


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    tx = TransactionService(db).create(current_user.id, payload)
    return _to_transaction_response(tx)


@router.post("/bulk", response_model=BulkTransactionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_bulk_transactions(
    payload: BulkTransactionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkTransactionCreateResponse:
    created, errors = TransactionService(db).create_bulk(current_user.id, payload.transactions)
    return BulkTransactionCreateResponse(
        created_count=len(created),
        failed_count=len(errors),
        created=[_to_transaction_response(item) for item in created],
        errors=errors,
    )


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    tx = TransactionService(db).update(current_user.id, transaction_id, payload)
    return _to_transaction_response(tx)


@router.delete("/{transaction_id}", response_model=MessageResponse)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    TransactionService(db).delete(current_user.id, transaction_id)
    return MessageResponse(message="Transaction deleted successfully")


def _to_transaction_response(record) -> TransactionResponse:
    return TransactionResponse(
        id=record.id,
        amount=record.amount,
        type=record.type,
        transaction_date=record.transaction_date,
        category_id=record.category_id,
        category_name=record.category.name if getattr(record, "category", None) else None,
        description=record.description,
    )
