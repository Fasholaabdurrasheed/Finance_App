from decimal import Decimal
from typing import Any

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


class PercentileItem(BaseModel):
    percentile: int
    value: float


class DescriptiveStatisticsDetailResponse(BaseModel):
    count: int
    mean: float | None
    median: float | None
    mode: list[float]
    variance: float | None
    standard_deviation: float | None
    quartile_1: float | None
    quartile_2: float | None
    quartile_3: float | None
    percentiles: list[PercentileItem]
    interquartile_range: float | None
    coefficient_of_variation: float | None
    min_value: float | None
    max_value: float | None
    range_value: float | None


class HistogramBin(BaseModel):
    left: float
    right: float
    count: int


class DensityPoint(BaseModel):
    x: float
    y: float


class BoxPlotData(BaseModel):
    min_value: float
    q1: float
    median: float
    q3: float
    max_value: float


class DistributionSummaryResponse(BaseModel):
    count: int
    mean: float | None
    standard_deviation: float | None
    skewness: float | None
    kurtosis: float | None
    jarque_bera_statistic: float | None
    normality_p_value: float | None
    is_approximately_normal: bool


class DistributionAnalysisResponse(BaseModel):
    transaction_type: str
    summary: DistributionSummaryResponse
    histogram: list[HistogramBin]
    density_curve: list[DensityPoint]
    boxplot: BoxPlotData | None


class ThresholdProbability(BaseModel):
    threshold: float
    probability: float


class AnomalyPoint(BaseModel):
    transaction_id: int
    transaction_date: str
    amount: float
    z_score: float


class ConfidenceIntervalResponse(BaseModel):
    confidence_level: float
    lower_bound: float | None
    upper_bound: float | None
    mean: float | None


class ProbabilityRiskAnalysisResponse(BaseModel):
    overspending_probability: float
    overspending_threshold: float
    savings_risk_probability: float
    threshold_probabilities: list[ThresholdProbability]
    anomaly_count: int
    anomalies: list[AnomalyPoint]
    confidence_interval: ConfidenceIntervalResponse
    architecture_notes: list[str]


class PlotlyFigureResponse(BaseModel):
    data: list[dict[str, Any]]
    layout: dict[str, Any]


class TimeSeriesPoint(BaseModel):
    period: str
    income: float
    expenses: float
    net: float
    moving_average: float | None
    rolling_mean: float | None
    rolling_variance: float | None
    monthly_growth_rate: float | None
    cumulative_expenses: float


class SeasonalIndexPoint(BaseModel):
    month: int
    seasonal_index: float


class TrendSummary(BaseModel):
    slope: float
    direction: str


class TimeSeriesAnalyticsResponse(BaseModel):
    points: list[TimeSeriesPoint]
    trend: TrendSummary
    seasonal_indices: list[SeasonalIndexPoint]