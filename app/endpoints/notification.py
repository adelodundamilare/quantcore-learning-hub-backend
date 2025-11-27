from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.models.user import User
from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.notification import Notification
from app.services.notification import notification_service
from app.core.cache import cache
from app.core.decorators import cache_endpoint

router = APIRouter()

@router.get("/", response_model=APIResponse[List[Notification]])
@cache_endpoint(ttl=60)
async def get_my_notifications(
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Retrieve notifications for the current user."""
    data = notification_service.get_user_notifications(db, user_id=user.id, skip=skip, limit=limit)
    return APIResponse(message="Notifications fetched successfully", data=data)

@router.get("/unread_count", response_model=APIResponse[int])
@cache_endpoint(ttl=30)
async def get_unread_notifications_count(
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user)
):
    """Get the count of unread notifications for the current user."""
    count = notification_service.get_unread_count(db, user_id=user.id)
    return APIResponse(message="Unread notifications count fetched successfully", data=count)

@router.post("/{notification_id}/read", response_model=APIResponse[Notification])
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_user)
):
    """Mark a specific notification as read."""
    notification = notification_service.mark_notification_as_read(db, notification_id=notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found or not authorized")
    await cache.invalidate_user_cache(user.id)
    return APIResponse(message="Notification marked as read", data=notification)

@router.post("/mark_all_read",response_model=APIResponse[None])
async def mark_all_notifications_as_read(
    db: Session = Depends(deps.get_transactional_db),
    user: User = Depends(deps.get_current_user)
):
    """Mark all unread notifications for the current user as read."""
    notification_service.mark_all_notifications_as_read(db, user_id=user.id)
    await cache.invalidate_user_cache(user.id)
    return APIResponse(message="All notifications marked as read")
