from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    CategoryAnalyticsItem,
    DescriptiveStatisticsResponse,
    MonthlyAnalyticsItem,
    SpendingTrendItem,
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