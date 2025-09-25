from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.notification import Notification
from app.services.notification import notification_service
from app.schemas.user import UserContext

router = APIRouter()

@router.get("/", response_model=List[Notification])
def get_my_notifications(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    """Retrieve notifications for the current user."""
    return notification_service.get_user_notifications(db, user_id=context.user.id, skip=skip, limit=limit)

@router.get("/unread_count", response_model=int)
def get_unread_notifications_count(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Get the count of unread notifications for the current user."""
    return notification_service.get_unread_count(db, user_id=context.user.id)

@router.post("/{notification_id}/read", response_model=APIResponse[Notification])
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_active_user_with_context)
):
    """Mark a specific notification as read."""
    notification = notification_service.mark_notification_as_read(db, notification_id=notification_id)
    if not notification or notification.user_id != context.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found or not authorized")
    return APIResponse(message="Notification marked as read", data=notification)

@router.post("/mark_all_read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_as_read(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Mark all unread notifications for the current user as read."""
    notification_service.mark_all_notifications_as_read(db, user_id=context.user.id)
    return
