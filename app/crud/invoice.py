from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud.base import CRUDBase
from app.models.billing import Invoice
from pydantic import BaseModel


class CRUDInvoice(CRUDBase[Invoice, BaseModel, BaseModel]):
    def get_by_stripe_invoice_id(self, db: Session, *, stripe_invoice_id: str) -> Optional[Invoice]:
        return db.query(self.model).filter(self.model.stripe_invoice_id == stripe_invoice_id).first()

    def get_multi_by_school(self, db: Session, *, school_id: int) -> List[Invoice]:
        return db.query(self.model).filter(self.model.school_id == school_id).all()

    def get_multi_by_school_and_status(self, db: Session, *, school_id: int, status: str) -> List[Invoice]:
        return db.query(self.model).filter(self.model.school_id == school_id, self.model.status == status).all()

    def create(self, db: Session, *, obj_in: Invoice) -> Invoice:
        db.add(obj_in)
        db.commit()
        db.refresh(obj_in)
        return obj_in

    def update(self, db: Session, *, db_obj: Invoice, obj_in: dict) -> Invoice:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

invoice = CRUDInvoice(Invoice)
