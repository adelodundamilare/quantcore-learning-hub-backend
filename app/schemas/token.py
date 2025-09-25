from pydantic import BaseModel
from typing import List
from .user import UserContext

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    user_id: int | None = None
    school_id: int | None = None
    role_id: int | None = None

class LoginResponse(BaseModel):
    """Response for the login endpoint."""
    token: Token
    contexts: List[UserContext] = []
