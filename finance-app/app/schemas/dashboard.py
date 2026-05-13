from decimal import Decimal

from pydantic import BaseModel


class CategorySummary(BaseModel):
    category_id: int | None
    category_name: str
    total: Decimal


class MonthlySummary(BaseModel):
    year: int
    month: int
    income: Decimal
    expenses: Decimal


class DashboardSummaryResponse(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    current_balance: Decimal
    monthly_summaries: list[MonthlySummary]
    category_summaries: list[CategorySummary]
