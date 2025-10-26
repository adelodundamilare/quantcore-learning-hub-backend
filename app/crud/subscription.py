from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud.base import CRUDBase
from app.models.billing import Subscription
from pydantic import BaseModel


class CRUDSubscription(CRUDBase[Subscription, BaseModel, BaseModel]):
    def get_by_stripe_subscription_id(self, db: Session, *, stripe_subscription_id: str) -> Optional[Subscription]:
        return db.query(self.model).filter(self.model.stripe_subscription_id == stripe_subscription_id).first()

    def get_multi_by_user(self, db: Session, *, user_id: int) -> List[Subscription]:
        return db.query(self.model).filter(self.model.user_id == user_id).all()

    def create(self, db: Session, *, obj_in: Subscription) -> Subscription:
        db.add(obj_in)
        db.commit()
        db.refresh(obj_in)
        return obj_in

    def update(self, db: Session, *, db_obj: Subscription, obj_in: dict) -> Subscription:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_active_count(self, db: Session) -> int:
        return db.query(self.model).filter(self.model.status == "active").count()

subscription = CRUDSubscription(Subscription)
