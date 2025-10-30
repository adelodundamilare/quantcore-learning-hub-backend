from app.crud.base import CRUDBase
from app.models.billing import StripePrice
from app.schemas.billing import StripePriceSchema
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

class CRUDStripePrice(CRUDBase[StripePrice, BaseModel, BaseModel]):
    def get_by_stripe_price_id(self, db: Session, *, stripe_price_id: str) -> Optional[StripePrice]:
        return db.query(self.model).filter(self.model.stripe_price_id == stripe_price_id).first()

stripe_price = CRUDStripePrice(StripePrice)
