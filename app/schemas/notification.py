from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class NotificationBase(BaseModel):
    """Base schema for a notification."""
    message: str
    link: Optional[str] = None
    notification_type: Optional[str] = None

class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""
    user_id: int

class NotificationUpdate(BaseModel):
    """Schema for updating a notification (e.g., marking as read)."""
    is_read: bool

class Notification(NotificationBase):
    """Schema for reading a notification, includes ID and status."""
    id: int
    user_id: int
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
