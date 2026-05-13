from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import BaseModel


class ImportJob(BaseModel):
    __tablename__ = "import_jobs"

    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    logs = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    upload = relationship("Upload", back_populates="jobs")
