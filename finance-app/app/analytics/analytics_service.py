from decimal import Decimal

from sqlalchemy import case, extract, func
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.analytics import (
    CategoryAnalyticsItem,
    DescriptiveStatisticsResponse,
    MonthlyAnalyticsItem,
    SpendingTrendItem,
    YearlyAnalyticsItem,
)
from app.schemas.dashboard import CategorySummary, DashboardSummaryResponse, MonthlySummary


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_summary(self, user_id: int) -> DashboardSummaryResponse:
        totals = (
            self.db.query(
                func.coalesce(
                    func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)),
                    0,
                ).label("income"),
                func.coalesce(
                    func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)),
                    0,
                ).label("expenses"),
            )
            .filter(Transaction.user_id == user_id)
            .first()
        )

        total_income = Decimal(totals.income or 0)
        total_expenses = Decimal(totals.expenses or 0)

        monthly_rows = (
            self.db.query(
                extract("year", Transaction.transaction_date).label("year"),
                extract("month", Transaction.transaction_date).label("month"),
                func.coalesce(
                    func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)),
                    0,
                ).label("income"),
                func.coalesce(
                    func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)),
                    0,
                ).label("expenses"),
            )
            .filter(Transaction.user_id == user_id)
            .group_by(
                extract("year", Transaction.transaction_date),
                extract("month", Transaction.transaction_date),
            )
            .order_by(
                extract("year", Transaction.transaction_date).desc(),
                extract("month", Transaction.transaction_date).desc(),
            )
            .all()
        )

        category_rows = (
            self.db.query(
                Category.id.label("category_id"),
                func.coalesce(Category.name, "Uncategorized").label("category_name"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .filter(Transaction.user_id == user_id)
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        monthly_summaries = [
            MonthlySummary(
                year=int(row.year),
                month=int(row.month),
                income=Decimal(row.income or 0),
                expenses=Decimal(row.expenses or 0),
            )
            for row in monthly_rows
        ]

        category_summaries = [
            CategorySummary(
                category_id=row.category_id,
                category_name=row.category_name,
                total=Decimal(row.total or 0),
            )
            for row in category_rows
        ]

        return DashboardSummaryResponse(
            total_income=total_income,
            total_expenses=total_expenses,
            current_balance=total_income - total_expenses,
            monthly_summaries=monthly_summaries,
            category_summaries=category_summaries,
        )

    def monthly_summary(self, user_id: int) -> list[MonthlyAnalyticsItem]:
        rows = (
            self.db.query(
                extract("year", Transaction.transaction_date).label("year"),
                extract("month", Transaction.transaction_date).label("month"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("income"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("expenses"),
            )
            .filter(Transaction.user_id == user_id)
            .group_by(extract("year", Transaction.transaction_date), extract("month", Transaction.transaction_date))
            .order_by(extract("year", Transaction.transaction_date), extract("month", Transaction.transaction_date))
            .all()
        )
        return [
            MonthlyAnalyticsItem(
                year=int(row.year),
                month=int(row.month),
                income=Decimal(row.income or 0),
                expenses=Decimal(row.expenses or 0),
                net=Decimal(row.income or 0) - Decimal(row.expenses or 0),
            )
            for row in rows
        ]

    def yearly_summary(self, user_id: int) -> list[YearlyAnalyticsItem]:
        rows = (
            self.db.query(
                extract("year", Transaction.transaction_date).label("year"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("income"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("expenses"),
            )
            .filter(Transaction.user_id == user_id)
            .group_by(extract("year", Transaction.transaction_date))
            .order_by(extract("year", Transaction.transaction_date))
            .all()
        )
        return [
            YearlyAnalyticsItem(
                year=int(row.year),
                income=Decimal(row.income or 0),
                expenses=Decimal(row.expenses or 0),
                net=Decimal(row.income or 0) - Decimal(row.expenses or 0),
            )
            for row in rows
        ]

    def category_analysis(self, user_id: int) -> list[CategoryAnalyticsItem]:
        rows = (
            self.db.query(
                Category.id.label("category_id"),
                func.coalesce(Category.name, "Uncategorized").label("category_name"),
                func.count(Transaction.id).label("transaction_count"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("total_income"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("total_expenses"),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .filter(Transaction.user_id == user_id)
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )
        return [
            CategoryAnalyticsItem(
                category_id=row.category_id,
                category_name=row.category_name,
                transaction_count=int(row.transaction_count or 0),
                total_income=Decimal(row.total_income or 0),
                total_expenses=Decimal(row.total_expenses or 0),
                net=Decimal(row.total_income or 0) - Decimal(row.total_expenses or 0),
            )
            for row in rows
        ]

    def spending_trends(self, user_id: int) -> list[SpendingTrendItem]:
        cumulative = Decimal("0.00")
        trends: list[SpendingTrendItem] = []
        for item in self.monthly_summary(user_id):
            cumulative += item.expenses
            trends.append(
                SpendingTrendItem(
                    year=item.year,
                    month=item.month,
                    expenses=item.expenses,
                    cumulative_expenses=cumulative,
                )
            )
        return trends

    def descriptive_statistics(self, user_id: int) -> DescriptiveStatisticsResponse:
        row = (
            self.db.query(
                func.count(Transaction.id).label("total_transactions"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("total_income"),
                func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("total_expenses"),
                func.min(Transaction.amount).label("min_amount"),
                func.max(Transaction.amount).label("max_amount"),
                func.avg(Transaction.amount).label("mean_amount"),
                func.percentile_cont(0.5).within_group(Transaction.amount).label("median_amount"),
                func.stddev_pop(Transaction.amount).label("std_amount"),
            )
            .filter(Transaction.user_id == user_id)
            .first()
        )
        return DescriptiveStatisticsResponse(
            total_transactions=int(row.total_transactions or 0),
            total_income=Decimal(row.total_income or 0),
            total_expenses=Decimal(row.total_expenses or 0),
            min_amount=Decimal(row.min_amount) if row.min_amount is not None else None,
            max_amount=Decimal(row.max_amount) if row.max_amount is not None else None,
            mean_amount=Decimal(str(row.mean_amount)) if row.mean_amount is not None else None,
            median_amount=Decimal(str(row.median_amount)) if row.median_amount is not None else None,
            std_amount=Decimal(str(row.std_amount)) if row.std_amount is not None else None,
        )
