from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    message: str
    data: Optional[Any] = None
