from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.analytics import (
    CategoryAnalyticsItem,
    DescriptiveStatisticsDetailResponse,
    DescriptiveStatisticsResponse,
    DistributionAnalysisResponse,
    MonthlyAnalyticsItem,
    PlotlyFigureResponse,
    ProbabilityRiskAnalysisResponse,
    SpendingTrendItem,
    TimeSeriesAnalyticsResponse,
    YearlyAnalyticsItem,
)
from app.analytics.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/monthly-summary", response_model=list[MonthlyAnalyticsItem])
async def monthly_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MonthlyAnalyticsItem]:
    return AnalyticsService(db).monthly_summary(current_user.id)


@router.get("/yearly-summary", response_model=list[YearlyAnalyticsItem])
async def yearly_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[YearlyAnalyticsItem]:
    return AnalyticsService(db).yearly_summary(current_user.id)


@router.get("/category-analysis", response_model=list[CategoryAnalyticsItem])
async def category_analysis(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CategoryAnalyticsItem]:
    return AnalyticsService(db).category_analysis(current_user.id)


@router.get("/spending-trends", response_model=list[SpendingTrendItem])
async def spending_trends(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SpendingTrendItem]:
    return AnalyticsService(db).spending_trends(current_user.id)


@router.get("/descriptive-stats", response_model=DescriptiveStatisticsResponse)
async def descriptive_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DescriptiveStatisticsResponse:
    return AnalyticsService(db).descriptive_statistics(current_user.id)


@router.get("/descriptive-stats-detailed", response_model=DescriptiveStatisticsDetailResponse)
async def descriptive_stats_detailed(
    tx_type: TransactionType | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DescriptiveStatisticsDetailResponse:
    return AnalyticsService(db).descriptive_statistics_detail(current_user.id, tx_type=tx_type)


@router.get("/distribution-analysis", response_model=DistributionAnalysisResponse)
async def distribution_analysis(
    tx_type: TransactionType = Query(default=TransactionType.EXPENSE),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionAnalysisResponse:
    return AnalyticsService(db).distribution_analysis(current_user.id, tx_type=tx_type)


@router.get("/probability-risk", response_model=ProbabilityRiskAnalysisResponse)
async def probability_risk(
    overspending_threshold: float | None = Query(default=None, ge=0),
    thresholds: list[float] | None = Query(default=None),
    anomaly_z_threshold: float = Query(default=2.5, ge=0.1),
    confidence_level: float = Query(default=0.95, ge=0.8, le=0.99),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProbabilityRiskAnalysisResponse:
    return AnalyticsService(db).probability_risk_analysis(
        current_user.id,
        overspending_threshold=overspending_threshold,
        thresholds=thresholds,
        z_threshold=anomaly_z_threshold,
        confidence_level=confidence_level,
    )


@router.get("/visualizations/{chart_type}", response_model=PlotlyFigureResponse)
async def analytics_visualization(
    chart_type: str,
    moving_window: int = Query(default=3, ge=2, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlotlyFigureResponse:
    try:
        return AnalyticsService(db).plotly_visualization(
            user_id=current_user.id,
            chart_type=chart_type,
            moving_window=moving_window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/time-series", response_model=TimeSeriesAnalyticsResponse)
async def time_series(
    moving_window: int = Query(default=3, ge=2, le=30),
    rolling_window: int = Query(default=3, ge=2, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimeSeriesAnalyticsResponse:
    return AnalyticsService(db).time_series_analytics(
        user_id=current_user.id,
        moving_window=moving_window,
        rolling_window=rolling_window,
    )