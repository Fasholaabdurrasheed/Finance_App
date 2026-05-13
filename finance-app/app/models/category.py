from sqlalchemy import Column, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.models.enums import TransactionType


class Category(BaseModel):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", "type", name="uq_owner_category_name_type"),
    )

    name = Column(String(100), nullable=False)
    type = Column(Enum(TransactionType, name="category_type_enum"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    owner = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True, index=True)
    upload = relationship("Upload")
