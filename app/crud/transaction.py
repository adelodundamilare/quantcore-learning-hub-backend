from app.crud.base import CRUDBase
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionSchema

class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionSchema]):
    pass

transaction = CRUDTransaction(Transaction)
