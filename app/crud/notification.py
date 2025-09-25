from sqlalchemy.orm import Session
from typing import List

from app.crud.base import CRUDBase
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate

class CRUDNotification(CRUDBase[Notification, NotificationCreate, NotificationUpdate]):
    """CRUD operations for Notifications."""

    def get_for_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[Notification]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

    def get_unread_for_user(self, db: Session, *, user_id: int) -> List[Notification]:
        return db.query(self.model).filter(self.model.user_id == user_id, self.model.is_read == False).all()

    def mark_as_read(self, db: Session, *, notification_id: int) -> Notification | None:
        notification = self.get(db, id=notification_id)
        if notification:
            notification.is_read = True
            db.add(notification)
        return notification

    def mark_all_as_read(self, db: Session, *, user_id: int) -> None:
        db.query(self.model).filter(self.model.user_id == user_id, self.model.is_read == False).update({"is_read": True})
        db.commit()

notification = CRUDNotification(Notification)
ication = CRUDNotification(Notification)
