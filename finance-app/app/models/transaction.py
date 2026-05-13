from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.models.enums import TransactionType


class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(Enum(TransactionType, name="transaction_type_enum"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255), nullable=True)
    transaction_date = Column(Date, nullable=False, index=True)

    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True, index=True)
    upload = relationship("Upload")
