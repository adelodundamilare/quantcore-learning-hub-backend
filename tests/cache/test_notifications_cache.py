import time
import uuid
import pytest
from sqlalchemy.orm import Session
from app.services.notification import notification_service
from app.core.cache_config import CACHE_KEYS
from app.core.cache import cache
import asyncio

class CallCounter:
    def __init__(self):
        self.count=0
    def __call__(self,*args,**kwargs):
        self.count+=1
        return []

@pytest.mark.asyncio
async def test_notifications_cache_hit_and_invalidate(db_session: Session, monkeypatch, user_factory):
    counter=CallCounter()
    monkeypatch.setattr("app.crud.notification.notification.get_for_user",counter,raising=True)
    user=user_factory(f"cache-notif-{uuid.uuid4().hex}@test.com")
    r1=notification_service.get_user_notifications(db_session,user_id=user.id,skip=0,limit=100)
    r2=notification_service.get_user_notifications(db_session,user_id=user.id,skip=0,limit=100)
    assert counter.count==1
    notification_service.create_notification(db_session,user_id=user.id,message="hi")

    cache_key = CACHE_KEYS["notifications_user"].format(user.id, 0, 100)
    await cache.delete(cache_key)

    r3=notification_service.get_user_notifications(db_session,user_id=user.id,skip=0,limit=100)
    assert counter.count==2