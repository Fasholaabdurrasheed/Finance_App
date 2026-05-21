from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import NotificationSeverity, NotificationType


class ReminderPreferenceUpdate(BaseModel):
    enable_daily_reminder: bool | None = None
    enable_weekly_reminder: bool | None = None
    enable_monthly_reminder: bool | None = None
    enable_business_alerts: bool | None = None
    enable_financial_summary: bool | None = None
    preferred_hour_utc: int | None = Field(default=None, ge=0, le=23)
    overspending_threshold: float | None = Field(default=None, ge=0)
    anomaly_zscore_threshold: float | None = Field(default=None, ge=0.1)


class ReminderPreferenceResponse(BaseModel):
    enable_daily_reminder: bool
    enable_weekly_reminder: bool
    enable_monthly_reminder: bool
    enable_business_alerts: bool
    enable_financial_summary: bool
    preferred_hour_utc: int
    overspending_threshold: float
    anomaly_zscore_threshold: float
    last_daily_scan_at: datetime | None
    last_weekly_scan_at: datetime | None
    last_monthly_scan_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: NotificationType
    severity: NotificationSeverity
    is_read: bool
    metadata_json: dict[str, Any] | None
    triggered_at: datetime

    model_config = {"from_attributes": True}


class NotificationMarkReadResponse(BaseModel):
    success: bool = True
    message: str


class NotificationScanTriggerResponse(BaseModel):
    success: bool = True
    message: str
