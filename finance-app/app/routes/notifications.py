from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationMarkReadResponse,
    NotificationResponse,
    NotificationScanTriggerResponse,
    ReminderPreferenceResponse,
    ReminderPreferenceUpdate,
)
from app.services.notification_service import NotificationService, run_scan_for_user_background

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationResponse]:
    rows = NotificationService(db).list_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )
    return [NotificationResponse.model_validate(item) for item in rows]


@router.post("/read/{notification_id}", response_model=NotificationMarkReadResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationMarkReadResponse:
    NotificationService(db).mark_notification_read(current_user.id, notification_id)
    return NotificationMarkReadResponse(message="Notification marked as read")


@router.get("/preferences", response_model=ReminderPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderPreferenceResponse:
    pref = NotificationService(db).get_preferences(current_user.id)
    return ReminderPreferenceResponse.model_validate(pref)


@router.put("/preferences", response_model=ReminderPreferenceResponse)
async def update_preferences(
    payload: ReminderPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderPreferenceResponse:
    pref = NotificationService(db).update_preferences(current_user.id, payload)
    return ReminderPreferenceResponse.model_validate(pref)


@router.post("/scan", response_model=NotificationScanTriggerResponse)
async def run_notification_scan(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> NotificationScanTriggerResponse:
    background_tasks.add_task(run_scan_for_user_background, current_user.id)
    return NotificationScanTriggerResponse(message="Notification scan triggered")
