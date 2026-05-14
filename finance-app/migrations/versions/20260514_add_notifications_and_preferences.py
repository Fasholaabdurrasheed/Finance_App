"""add notifications and reminder preferences tables

Revision ID: 20260514_add_notifications_and_preferences
Revises: 20260513_add_import_jobs
Create Date: 2026-05-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260514_add_notifications_and_preferences"
down_revision = "20260513_add_import_jobs"
branch_labels = None
depends_on = None


notification_type_enum = sa.Enum(
    "reminder",
    "anomaly",
    "summary",
    "business_alert",
    name="notification_type_enum",
)
notification_severity_enum = sa.Enum("info", "warning", "critical", name="notification_severity_enum")


def upgrade():
    bind = op.get_bind()
    notification_type_enum.create(bind, checkfirst=True)
    notification_severity_enum.create(bind, checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("severity", notification_severity_enum, nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_severity", "notifications", ["severity"])
    op.create_index("ix_notifications_triggered_at", "notifications", ["triggered_at"])

    op.create_table(
        "reminder_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("enable_daily_reminder", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enable_weekly_reminder", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enable_monthly_reminder", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enable_business_alerts", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enable_financial_summary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("preferred_hour_utc", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("overspending_threshold", sa.Float(), nullable=False, server_default="1000"),
        sa.Column("anomaly_zscore_threshold", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("last_daily_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_weekly_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_monthly_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_reminder_preferences_user_id"),
    )
    op.create_index("ix_reminder_preferences_user_id", "reminder_preferences", ["user_id"])


def downgrade():
    op.drop_index("ix_reminder_preferences_user_id", table_name="reminder_preferences")
    op.drop_table("reminder_preferences")

    op.drop_index("ix_notifications_triggered_at", table_name="notifications")
    op.drop_index("ix_notifications_severity", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    bind = op.get_bind()
    notification_severity_enum.drop(bind, checkfirst=True)
    notification_type_enum.drop(bind, checkfirst=True)
