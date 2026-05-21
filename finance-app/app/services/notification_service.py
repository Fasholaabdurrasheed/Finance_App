from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.enums import NotificationSeverity, NotificationType, TransactionType
from app.models.notification import Notification
from app.models.reminder_preference import ReminderPreference
from app.models.transaction import Transaction
from app.schemas.notification import ReminderPreferenceUpdate


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def get_preferences(self, user_id: int) -> ReminderPreference:
        pref = self.db.query(ReminderPreference).filter(ReminderPreference.user_id == user_id).first()
        if pref:
            return pref

        pref = ReminderPreference(user_id=user_id)
        self.db.add(pref)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def update_preferences(self, user_id: int, payload: ReminderPreferenceUpdate) -> ReminderPreference:
        pref = self.get_preferences(user_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(pref, key, value)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def list_notifications(self, user_id: int, unread_only: bool = False, limit: int = 100) -> list[Notification]:
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        return query.order_by(Notification.triggered_at.desc(), Notification.id.desc()).limit(limit).all()

    def mark_notification_read(self, user_id: int, notification_id: int) -> None:
        notification = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        notification.is_read = True
        self.db.commit()

    def run_user_scan(self, user_id: int) -> int:
        pref = self.get_preferences(user_id)
        created = 0

        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        if pref.enable_daily_reminder and not self._has_record_for_day(user_id, yesterday):
            created += self._create_notification_if_not_exists(
                user_id=user_id,
                title="Daily finance reminder",
                message=f"No financial record was found for {yesterday.isoformat()}. Add entries to keep your analytics reliable.",
                ntype=NotificationType.REMINDER,
                severity=NotificationSeverity.INFO,
                unique_scope=f"daily:{yesterday.isoformat()}",
            )
            pref.last_daily_scan_at = datetime.now(timezone.utc)

        if pref.enable_weekly_reminder and not self._has_records_in_range(user_id, start_of_week, today):
            created += self._create_notification_if_not_exists(
                user_id=user_id,
                title="Weekly monitoring reminder",
                message="No records found for the current week. Weekly tracking helps detect spending drift early.",
                ntype=NotificationType.REMINDER,
                severity=NotificationSeverity.WARNING,
                unique_scope=f"weekly:{start_of_week.isoformat()}",
            )
            pref.last_weekly_scan_at = datetime.now(timezone.utc)

        if pref.enable_monthly_reminder and not self._has_records_in_range(user_id, start_of_month, today):
            created += self._create_notification_if_not_exists(
                user_id=user_id,
                title="Monthly completeness reminder",
                message="No records have been captured this month. Monthly coverage is required for trend and growth analytics.",
                ntype=NotificationType.REMINDER,
                severity=NotificationSeverity.WARNING,
                unique_scope=f"monthly:{start_of_month.isoformat()}",
            )
            pref.last_monthly_scan_at = datetime.now(timezone.utc)

        created += self._run_overspending_alerts(user_id=user_id, threshold=pref.overspending_threshold)
        created += self._run_anomaly_alerts(user_id=user_id, z_threshold=pref.anomaly_zscore_threshold)
        if pref.enable_financial_summary:
            created += self._run_financial_summary(user_id=user_id)

        self.db.commit()
        return created

    def _run_overspending_alerts(self, user_id: int, threshold: float) -> int:
        month_start = date.today().replace(day=1)
        expense_total = (
            self.db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= month_start,
            )
            .scalar()
        )
        amount = float(expense_total or 0)
        if amount > threshold:
            return self._create_notification_if_not_exists(
                user_id=user_id,
                title="Overspending threshold exceeded",
                message=f"Current month expenses ({amount:.2f}) exceeded your threshold ({threshold:.2f}).",
                ntype=NotificationType.BUSINESS_ALERT,
                severity=NotificationSeverity.CRITICAL,
                unique_scope=f"overspending:{month_start.isoformat()}",
                metadata_json={"expense_total": amount, "threshold": threshold},
            )
        return 0

    def _run_anomaly_alerts(self, user_id: int, z_threshold: float) -> int:
        rows = (
            self.db.query(Transaction.id, Transaction.amount, Transaction.transaction_date)
            .filter(Transaction.user_id == user_id, Transaction.type == TransactionType.EXPENSE)
            .order_by(Transaction.transaction_date.desc())
            .limit(120)
            .all()
        )
        if len(rows) < 10:
            return 0

        df = pd.DataFrame(
            [{"id": item.id, "amount": float(item.amount), "transaction_date": item.transaction_date} for item in rows]
        )
        std = float(df["amount"].std(ddof=0))
        if std <= 0:
            return 0

        mean = float(df["amount"].mean())
        df["z"] = (df["amount"] - mean) / std
        anomalies = df[df["z"].abs() >= z_threshold].head(5)
        created = 0
        for _, anomaly in anomalies.iterrows():
            unique_scope = f"anomaly:{int(anomaly['id'])}"
            created += self._create_notification_if_not_exists(
                user_id=user_id,
                title="Spending anomaly detected",
                message=f"Transaction {int(anomaly['id'])} appears anomalous with z-score {float(anomaly['z']):.2f}.",
                ntype=NotificationType.ANOMALY,
                severity=NotificationSeverity.WARNING,
                unique_scope=unique_scope,
                metadata_json={
                    "transaction_id": int(anomaly["id"]),
                    "z_score": float(anomaly["z"]),
                    "amount": float(anomaly["amount"]),
                },
            )
        return created

    def _run_financial_summary(self, user_id: int) -> int:
        month_start = date.today().replace(day=1)
        totals = (
            self.db.query(
                func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("income"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("expenses"),
            )
            .filter(Transaction.user_id == user_id, Transaction.transaction_date >= month_start)
            .first()
        )
        income = float(totals.income or 0)
        expenses = float(totals.expenses or 0)
        net = income - expenses

        return self._create_notification_if_not_exists(
            user_id=user_id,
            title="Financial summary snapshot",
            message=(
                f"Month-to-date summary - Income: {income:.2f}, Expenses: {expenses:.2f}, Net: {net:.2f}."
            ),
            ntype=NotificationType.SUMMARY,
            severity=NotificationSeverity.INFO,
            unique_scope=f"summary:{month_start.isoformat()}",
            metadata_json={"income": income, "expenses": expenses, "net": net},
        )

    def _has_record_for_day(self, user_id: int, day: date) -> bool:
        count = (
            self.db.query(func.count(Transaction.id))
            .filter(Transaction.user_id == user_id, Transaction.transaction_date == day)
            .scalar()
        )
        return bool(count)

    def _has_records_in_range(self, user_id: int, start: date, end: date) -> bool:
        count = (
            self.db.query(func.count(Transaction.id))
            .filter(
                Transaction.user_id == user_id,
                and_(Transaction.transaction_date >= start, Transaction.transaction_date <= end),
            )
            .scalar()
        )
        return bool(count)

    def _create_notification_if_not_exists(
        self,
        user_id: int,
        title: str,
        message: str,
        ntype: NotificationType,
        severity: NotificationSeverity,
        unique_scope: str,
        metadata_json: dict | None = None,
    ) -> int:
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        existing = (
            self.db.query(Notification.id)
            .filter(
                Notification.user_id == user_id,
                Notification.title == title,
                Notification.triggered_at >= start_of_day,
            )
            .first()
        )
        if existing:
            return 0

        payload = dict(metadata_json or {})
        payload["unique_scope"] = unique_scope

        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=ntype,
            severity=severity,
            metadata_json=payload,
        )
        self.db.add(notification)
        return 1


def run_scan_for_user_background(user_id: int) -> None:
    db = SessionLocal()
    try:
        NotificationService(db).run_user_scan(user_id)
    finally:
        db.close()
