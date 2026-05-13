from decimal import Decimal

from pydantic import BaseModel


class MonthlyAnalyticsItem(BaseModel):
    year: int
    month: int
    income: Decimal
    expenses: Decimal
    net: Decimal


class YearlyAnalyticsItem(BaseModel):
    year: int
    income: Decimal
    expenses: Decimal
    net: Decimal


class CategoryAnalyticsItem(BaseModel):
    category_id: int | None
    category_name: str
    transaction_count: int
    total_income: Decimal
    total_expenses: Decimal
    net: Decimal


class SpendingTrendItem(BaseModel):
    year: int
    month: int
    expenses: Decimal
    cumulative_expenses: Decimal


class DescriptiveStatisticsResponse(BaseModel):
    total_transactions: int
    total_income: Decimal
    total_expenses: Decimal
    min_amount: Decimal | None
    max_amount: Decimal | None
    mean_amount: Decimal | None
    median_amount: Decimal | None
    std_amount: Decimal | None