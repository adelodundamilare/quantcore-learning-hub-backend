from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TransactionSchema(BaseModel):
    id: int
    user_id: int
    initiator_id: Optional[int] = None
    amount: float
    transaction_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionCreate(BaseModel):
    user_id: int
    initiator_id: Optional[int] = None
    amount: float
    transaction_type: str
