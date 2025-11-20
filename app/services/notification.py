from sqlalchemy.orm import Session
from typing import List
from app.crud.notification import notification as crud_notification
from app.schemas.notification import NotificationCreate, NotificationUpdate, Notification
from app.utils.cache import cached, delete
from app.core.cache_constants import CACHE_TTL, CACHE_KEYS

class NotificationService:
    def create_notification(self, db: Session, *, user_id: int, message: str, link: str | None = None, notification_type: str | None = None) -> Notification:
        notification_in = NotificationCreate(user_id=user_id, message=message, link=link, notification_type=notification_type)
        n=crud_notification.create(db, obj_in=notification_in)
        delete(CACHE_KEYS["notifications_user"].format(user_id,0,100))
        delete(CACHE_KEYS["notifications_unread"].format(user_id))
        return n

    @cached(CACHE_KEYS["notifications_user"], ttl=CACHE_TTL["notifications_user"])
    def get_user_notifications(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Notification]:
        return crud_notification.get_for_user(db, user_id=user_id, skip=skip, limit=limit)

    @cached(CACHE_KEYS["notifications_unread"], ttl=CACHE_TTL["notifications_unread"])
    def get_unread_count(self, db: Session, *, user_id: int) -> int:
        return len(crud_notification.get_unread_for_user(db, user_id=user_id))

    def mark_notification_as_read(self, db: Session, *, notification_id: int) -> Notification | None:
        n=crud_notification.mark_as_read(db, notification_id=notification_id)
        if n:
            delete(CACHE_KEYS["notifications_user"].format(n.user_id,0,100))
            delete(CACHE_KEYS["notifications_unread"].format(n.user_id))
        return n

    def mark_all_notifications_as_read(self, db: Session, *, user_id: int) -> None:
        crud_notification.mark_all_as_read(db, user_id=user_id)
        delete(CACHE_KEYS["notifications_user"].format(user_id,0,100))
        delete(CACHE_KEYS["notifications_unread"].format(user_id))

notification_service = NotificationService()
