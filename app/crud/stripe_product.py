from app.crud.base import CRUDBase
from app.models.billing import StripeProduct
from app.schemas.billing import StripeProductCreate
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

class CRUDStripeProduct(CRUDBase[StripeProduct, StripeProductCreate, BaseModel]):
    def get_by_stripe_product_id(self, db: Session, *, stripe_product_id: str) -> Optional[StripeProduct]:
        return db.query(self.model).filter(self.model.stripe_product_id == stripe_product_id).first()

stripe_product = CRUDStripeProduct(StripeProduct)
