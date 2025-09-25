from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.one_time_token import TokenType

class OneTimeTokenBase(BaseModel):
    """Base schema for a one-time token."""
    token: str
    token_type: TokenType
    expires_at: datetime

class OneTimeTokenCreate(OneTimeTokenBase):
    """Schema for creating a one-time token."""
    user_id: int

class OneTimeToken(OneTimeTokenBase):
    """Schema for reading a one-time token."""
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
