from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class NotificationType(str, Enum):
    REMINDER = "reminder"
    ANOMALY = "anomaly"
    SUMMARY = "summary"
    BUSINESS_ALERT = "business_alert"


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
