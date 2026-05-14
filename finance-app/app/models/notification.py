from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.models.enums import NotificationSeverity, NotificationType


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType, name="notification_type_enum"), nullable=False, index=True)
    severity = Column(Enum(NotificationSeverity, name="notification_severity_enum"), nullable=False, index=True)
    is_read = Column(Boolean, nullable=False, default=False, server_default="false")
    metadata_json = Column(JSON, nullable=True)
    triggered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    user = relationship("User", back_populates="notifications")
