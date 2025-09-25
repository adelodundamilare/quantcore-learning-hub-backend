from pydantic import BaseModel
from datetime import datetime

class TokenDenylistBase(BaseModel):
    jti: str
    exp: datetime

class TokenDenylistCreate(TokenDenylistBase):
    pass

class TokenDenylist(TokenDenylistBase):
    id: int

    class Config:
        from_attributes = True