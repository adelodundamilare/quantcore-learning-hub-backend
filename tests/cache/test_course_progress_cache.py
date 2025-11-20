import pytest
import uuid
from sqlalchemy.orm import Session
from app.services.course_progress import course_progress_service
from app.core.cache_constants import CACHE_KEYS
from app.utils.cache import delete

class CallCounter:
    def __init__(self,ret):
        self.count=0
        self.ret=ret
    def __call__(self,*args,**kwargs):
        self.count+=1
        return self.ret

def test_user_enrollments_cache_and_invalidate(db_session: Session, monkeypatch, user_factory):
    user=user_factory(f"cache-progress-{uuid.uuid4().hex}@test.com")
    original=course_progress_service.get_user_enrollments
    calls={"n":0}

    def wrapper(db, user_id, ctx=None):
        calls["n"]+=1
        return original(db, user_id, ctx)

    monkeypatch.setattr("app.services.course_progress.course_progress_service.get_user_enrollments",wrapper,raising=False)

    class MockUser:
        def __init__(self, user_id):
            self.id = user_id
    class MockContext:
        def __init__(self, user_id):
            self.user = MockUser(user_id)

    ctx = MockContext(user.id)
    r1=course_progress_service.get_user_enrollments(db_session,user.id, ctx)
    r2=course_progress_service.get_user_enrollments(db_session,user.id, ctx)
    assert calls["n"]==1

    delete(CACHE_KEYS["user_enrollments"].format(user.id))
    r3=course_progress_service.get_user_enrollments(db_session,user.id, ctx)
    assert calls["n"]==2