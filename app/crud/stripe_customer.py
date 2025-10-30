from app.crud.base import CRUDBase
from app.models.billing import StripeCustomer
from app.schemas.billing import StripeCustomerCreate
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

class CRUDStripeCustomer(CRUDBase[StripeCustomer, StripeCustomerCreate, BaseModel]):
    def get_by_user_id(self, db: Session, *, user_id: int) -> Optional[StripeCustomer]:
        return db.query(self.model).filter(self.model.user_id == user_id).first()

    def get_by_stripe_customer_id(self, db: Session, *, stripe_customer_id: str) -> Optional[StripeCustomer]:
        return db.query(self.model).filter(self.model.stripe_customer_id == stripe_customer_id).first()

stripe_customer = CRUDStripeCustomer(StripeCustomer)