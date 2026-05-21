from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ReminderPreference(BaseModel):
    __tablename__ = "reminder_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_reminder_preferences_user_id"),)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    enable_daily_reminder = Column(Boolean, nullable=False, default=True, server_default="true")
    enable_weekly_reminder = Column(Boolean, nullable=False, default=True, server_default="true")
    enable_monthly_reminder = Column(Boolean, nullable=False, default=True, server_default="true")
    enable_business_alerts = Column(Boolean, nullable=False, default=True, server_default="true")
    enable_financial_summary = Column(Boolean, nullable=False, default=True, server_default="true")

    preferred_hour_utc = Column(Integer, nullable=False, default=18, server_default="18")
    overspending_threshold = Column(Float, nullable=False, default=1000.0, server_default="1000")
    anomaly_zscore_threshold = Column(Float, nullable=False, default=2.5, server_default="2.5")

    last_daily_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_weekly_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_monthly_scan_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reminder_preference")
