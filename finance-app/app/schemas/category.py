from pydantic import BaseModel, Field

from app.models.enums import TransactionType


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    type: TransactionType


class CategoryResponse(BaseModel):
    id: int
    name: str
    type: TransactionType
    owner_id: int | None

    model_config = {"from_attributes": True}
