from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    message: str
    data: Optional[Any] = None

class ContactAdminRequest(BaseModel):
    subject: str
    message: str
    screenshot_url: Optional[str] = None
