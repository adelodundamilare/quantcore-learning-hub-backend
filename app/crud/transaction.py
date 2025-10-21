from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionSchema
from typing import List

class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionSchema]):
    def get_multi_by_user_and_type(
        self, db: Session, *, user_id: int, transaction_type: str
    ) -> List[Transaction]:
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id, self.model.transaction_type == transaction_type)
            .all()
        )

transaction = CRUDTransaction(Transaction)
