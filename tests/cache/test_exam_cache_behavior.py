import pytest
from sqlalchemy.orm import Session
from app.services.exam import exam_service
from app.core.cache_config import CACHE_KEYS
from app.core.cache import cache
import asyncio

class FakeExam:
    def __init__(self,id):
        self.id=id

@pytest.mark.asyncio
async def test_exam_questions_cache_cycle(db_session: Session, monkeypatch):
    called={"q":0}
    def get_exam(db,id):
        return FakeExam(id)
    def get_by_exam(db,exam_id):
        called["q"]+=1
        return []
    monkeypatch.setattr("app.crud.exam.exam.get",get_exam,raising=True)
    monkeypatch.setattr("app.crud.question.question.get_by_exam",get_by_exam,raising=True)
    class Ctx: pass
    ctx=Ctx()
    from app.utils.permission import PermissionHelper as permission_helper
    monkeypatch.setattr(permission_helper,"is_student",lambda ctx: False,raising=True)
    monkeypatch.setattr(exam_service,"_require_exam_view_permission",lambda db,ctx,exam: None,raising=True)
    exam_service.get_exam_questions(db_session,1,ctx,True)
    exam_service.get_exam_questions(db_session,1,ctx,True)
    assert called["q"]==1
    await cache.delete(CACHE_KEYS["exam_questions"].format(1))
    exam_service.get_exam_questions(db_session,1,ctx,True)
    assert called["q"]==2