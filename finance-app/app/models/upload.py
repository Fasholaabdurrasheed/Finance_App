from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Upload(BaseModel):
    __tablename__ = "uploads"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    content_type = Column(String(100), nullable=True)
    size = Column(BigInteger, nullable=False)
    checksum = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    rows_total = Column(Integer, nullable=True)
    rows_inserted = Column(Integer, nullable=True)

    user = relationship("User", back_populates="uploads")
    jobs = relationship("ImportJob", back_populates="upload", cascade="all, delete-orphan")
