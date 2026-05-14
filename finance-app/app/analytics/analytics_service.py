from __future__ import annotations

from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import case, extract, func
from sqlalchemy.orm import Session

from app.analytics.statistics_utils import (
    boxplot_stats,
    compute_descriptive_statistics,
    compute_distribution_summary,
    gaussian_kde_points,
    histogram_bins,
)
from app.analytics.probability_utils import (
    empirical_probability_greater_than,
    normal_confidence_interval,
    zscore_anomalies,
)
from app.analytics.visualization_service import VisualizationService
from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.analytics import (
    CategoryAnalyticsItem,
    ConfidenceIntervalResponse,
    DescriptiveStatisticsDetailResponse,
    DescriptiveStatisticsResponse,
    DistributionAnalysisResponse,
    DistributionSummaryResponse,
    MonthlyAnalyticsItem,
    PercentileItem,
    PlotlyFigureResponse,
    ProbabilityRiskAnalysisResponse,
    SeasonalIndexPoint,
    SpendingTrendItem,
    ThresholdProbability,
    TimeSeriesAnalyticsResponse,
    TimeSeriesPoint,
    TrendSummary,
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

    def descriptive_statistics_detail(self, user_id: int, tx_type: TransactionType | None) -> DescriptiveStatisticsDetailResponse:
        frame = self._build_transaction_frame(user_id=user_id, tx_type=tx_type)
        stats = compute_descriptive_statistics(frame["amount"])
        return DescriptiveStatisticsDetailResponse(
            count=stats["count"],
            mean=stats["mean"],
            median=stats["median"],
            mode=stats["mode"],
            variance=stats["variance"],
            standard_deviation=stats["standard_deviation"],
            quartile_1=stats["quartile_1"],
            quartile_2=stats["quartile_2"],
            quartile_3=stats["quartile_3"],
            percentiles=[PercentileItem(**item) for item in stats["percentiles"]],
            interquartile_range=stats["interquartile_range"],
            coefficient_of_variation=stats["coefficient_of_variation"],
            min_value=stats["min_value"],
            max_value=stats["max_value"],
            range_value=stats["range_value"],
        )

    def distribution_analysis(self, user_id: int, tx_type: TransactionType) -> DistributionAnalysisResponse:
        frame = self._build_transaction_frame(user_id=user_id, tx_type=tx_type)
        summary = compute_distribution_summary(frame["amount"])
        return DistributionAnalysisResponse(
            transaction_type=tx_type.value,
            summary=DistributionSummaryResponse(**summary),
            histogram=histogram_bins(frame["amount"]),
            density_curve=gaussian_kde_points(frame["amount"]),
            boxplot=boxplot_stats(frame["amount"]),
        )

    def probability_risk_analysis(
        self,
        user_id: int,
        overspending_threshold: float | None,
        thresholds: list[float] | None,
        z_threshold: float,
        confidence_level: float,
    ) -> ProbabilityRiskAnalysisResponse:
        frame = self._build_transaction_frame(user_id=user_id)
        monthly = self._monthly_aggregates(frame)

        expenses = frame.loc[frame["type"] == TransactionType.EXPENSE.value, "amount"]

        if overspending_threshold is None:
            exp_mean = float(expenses.mean()) if not expenses.empty else 0.0
            exp_std = float(expenses.std(ddof=0)) if len(expenses) > 1 else 0.0
            overspending_threshold = exp_mean + exp_std

        overspending_probability = empirical_probability_greater_than(expenses, float(overspending_threshold))
        savings_risk_probability = float((monthly["net"] < 0).mean()) if not monthly.empty else 0.0

        threshold_probs: list[ThresholdProbability] = []
        for threshold in thresholds or []:
            prob = empirical_probability_greater_than(expenses, float(threshold))
            threshold_probs.append(ThresholdProbability(threshold=float(threshold), probability=prob))

        anomalies = zscore_anomalies(
            expenses_frame=frame[frame["type"] == TransactionType.EXPENSE.value],
            z_threshold=z_threshold,
        )
        ci = ConfidenceIntervalResponse(**normal_confidence_interval(expenses, confidence_level))

        architecture_notes = [
            "Monte Carlo extension point: replace empirical probabilities with simulated monthly paths.",
            "Bayesian extension point: use posterior spending distributions for dynamic risk thresholds.",
            "Stochastic modeling extension point: plug geometric/random-walk cash-flow simulators into the same response schema.",
        ]

        return ProbabilityRiskAnalysisResponse(
            overspending_probability=overspending_probability,
            overspending_threshold=float(overspending_threshold),
            savings_risk_probability=savings_risk_probability,
            threshold_probabilities=threshold_probs,
            anomaly_count=len(anomalies),
            anomalies=anomalies,
            confidence_interval=ci,
            architecture_notes=architecture_notes,
        )

    def plotly_visualization(self, user_id: int, chart_type: str, moving_window: int) -> PlotlyFigureResponse:
        frame = self._build_transaction_frame(user_id=user_id)
        viz = VisualizationService(frame)

        mapping = {
            "line": viz.plotly_line_income_expense,
            "pie": viz.plotly_pie_expenses_by_category,
            "bar": viz.plotly_bar_monthly_expenses,
            "scatter": viz.plotly_scatter_transactions,
            "boxplot": viz.plotly_box_expenses,
            "histogram": viz.plotly_histogram_amounts,
            "heatmap": viz.plotly_heatmap_weekday_month,
            "treemap": viz.plotly_treemap_category,
            "radar": viz.plotly_radar_top_categories,
            "moving_average": lambda: viz.plotly_moving_average(window=moving_window),
            "rolling_statistics": lambda: viz.plotly_rolling_statistics(window=moving_window),
        }
        builder = mapping.get(chart_type)
        if not builder:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        fig = builder()
        return PlotlyFigureResponse(data=fig["data"], layout=fig["layout"])

    def time_series_analytics(self, user_id: int, moving_window: int, rolling_window: int) -> TimeSeriesAnalyticsResponse:
        frame = self._build_transaction_frame(user_id=user_id)
        monthly = self._monthly_aggregates(frame)

        if monthly.empty:
            return TimeSeriesAnalyticsResponse(
                points=[],
                trend=TrendSummary(slope=0.0, direction="flat"),
                seasonal_indices=[],
            )

        monthly = monthly.sort_values("period").reset_index(drop=True)
        monthly["moving_average"] = monthly["expenses"].rolling(window=moving_window, min_periods=1).mean()
        monthly["rolling_mean"] = monthly["expenses"].rolling(window=rolling_window, min_periods=1).mean()
        monthly["rolling_variance"] = monthly["expenses"].rolling(window=rolling_window, min_periods=1).var().fillna(0)
        monthly["monthly_growth_rate"] = monthly["expenses"].pct_change().replace([np.inf, -np.inf], np.nan)
        monthly["cumulative_expenses"] = monthly["expenses"].cumsum()

        x = np.arange(len(monthly), dtype=float)
        y = monthly["expenses"].to_numpy(dtype=float)
        slope = float(np.polyfit(x, y, 1)[0]) if len(monthly) > 1 else 0.0
        direction = "flat"
        if slope > 0:
            direction = "upward"
        elif slope < 0:
            direction = "downward"

        seasonal_indices: list[SeasonalIndexPoint] = []
        if not frame.empty:
            working = frame.copy()
            working["month"] = working["transaction_date"].dt.month
            expense = working[working["type"] == TransactionType.EXPENSE.value]
            if not expense.empty:
                by_month = expense.groupby("month")["amount"].mean()
                overall = float(expense["amount"].mean())
                if overall != 0:
                    seasonal_indices = [
                        SeasonalIndexPoint(month=int(month), seasonal_index=float(value / overall))
                        for month, value in by_month.items()
                    ]

        points = [
            TimeSeriesPoint(
                period=str(row["period"]),
                income=float(row["income"]),
                expenses=float(row["expenses"]),
                net=float(row["net"]),
                moving_average=float(row["moving_average"]),
                rolling_mean=float(row["rolling_mean"]),
                rolling_variance=float(row["rolling_variance"]),
                monthly_growth_rate=float(row["monthly_growth_rate"]) if pd.notna(row["monthly_growth_rate"]) else None,
                cumulative_expenses=float(row["cumulative_expenses"]),
            )
            for _, row in monthly.iterrows()
        ]

        return TimeSeriesAnalyticsResponse(
            points=points,
            trend=TrendSummary(slope=slope, direction=direction),
            seasonal_indices=seasonal_indices,
        )

    def _build_transaction_frame(self, user_id: int, tx_type: TransactionType | None = None) -> pd.DataFrame:
        query = (
            self.db.query(
                Transaction.id.label("transaction_id"),
                Transaction.amount,
                Transaction.type,
                Transaction.transaction_date,
                func.coalesce(Category.name, "Uncategorized").label("category_name"),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .filter(Transaction.user_id == user_id)
        )
        if tx_type:
            query = query.filter(Transaction.type == tx_type)

        rows = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc()).all()
        frame = pd.DataFrame(
            [
                {
                    "transaction_id": int(item.transaction_id),
                    "amount": float(item.amount),
                    "type": item.type.value if isinstance(item.type, TransactionType) else str(item.type),
                    "transaction_date": item.transaction_date,
                    "category_name": item.category_name,
                }
                for item in rows
            ]
        )

        if frame.empty:
            return pd.DataFrame(columns=["transaction_id", "amount", "type", "transaction_date", "category_name"])

        frame["transaction_date"] = pd.to_datetime(frame["transaction_date"])
        return frame

    def _monthly_aggregates(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["period", "income", "expenses", "net"])

        grouped = (
            frame.assign(period=frame["transaction_date"].dt.to_period("M").astype(str))
            .groupby(["period", "type"], as_index=False)["amount"]
            .sum()
        )
        pivot = grouped.pivot(index="period", columns="type", values="amount").fillna(0).reset_index()
        if TransactionType.INCOME.value not in pivot:
            pivot[TransactionType.INCOME.value] = 0.0
        if TransactionType.EXPENSE.value not in pivot:
            pivot[TransactionType.EXPENSE.value] = 0.0

        pivot = pivot.rename(
            columns={
                TransactionType.INCOME.value: "income",
                TransactionType.EXPENSE.value: "expenses",
            }
        )
        pivot["net"] = pivot["income"] - pivot["expenses"]
        return pivot

