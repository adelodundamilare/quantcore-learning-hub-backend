from sqlalchemy.orm import Session
from typing import List

from app.crud.notification import notification as crud_notification
from app.schemas.notification import NotificationCreate, NotificationUpdate, Notification

class NotificationService:
    def create_notification(self, db: Session, *, user_id: int, message: str, link: str | None = None, notification_type: str | None = None) -> Notification:
        notification_in = NotificationCreate(user_id=user_id, message=message, link=link, notification_type=notification_type)
        n=crud_notification.create(db, obj_in=notification_in)
        return n

    def get_user_notifications(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Notification]:
        result = crud_notification.get_for_user(db, user_id=user_id, skip=skip, limit=limit)
        return result

    def get_unread_count(self, db: Session, *, user_id: int) -> int:
        result = len(crud_notification.get_unread_for_user(db, user_id=user_id))
        return result

    def mark_notification_as_read(self, db: Session, *, notification_id: int) -> Notification | None:
        n=crud_notification.mark_as_read(db, notification_id=notification_id)
        return n

    def mark_all_notifications_as_read(self, db: Session, *, user_id: int) -> None:
        crud_notification.mark_all_as_read(db, user_id=user_id)

notification_service = NotificationService()
