from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import TransactionType


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    type: TransactionType
    transaction_date: date
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    type: TransactionType | None = None
    transaction_date: date | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    type: TransactionType
    transaction_date: date
    category_id: int | None
    description: str | None

    model_config = {"from_attributes": True}
