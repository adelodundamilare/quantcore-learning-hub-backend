import pytest
from sqlalchemy.orm import Session
from app.services.exam import exam_service
from app.core.cache_constants import CACHE_KEYS
from app.utils.cache import delete, get, set
from app.utils.permission import PermissionHelper as permission_helper

class FakeExam:
    def __init__(self, id):
        self.id=id

def test_exam_questions_cache_and_invalidation(db_session: Session, monkeypatch, super_admin_token):
    called={"questions":0,"exam":0}

    def fake_get_by_exam(db, exam_id):
        called["questions"]+=1
        return []

    def fake_get_exam(db, id):
        called["exam"]+=1
        return FakeExam(id)

    delete(CACHE_KEYS["exam_questions"].format(1))

    monkeypatch.setattr("app.crud.question.question.get_by_exam", fake_get_by_exam, raising=True)
    monkeypatch.setattr("app.crud.exam.exam.get", fake_get_exam, raising=True)

    class MockUser:
        id = 1
    class MockCtx:
        user = MockUser()

    ctx = MockCtx()

    monkeypatch.setattr(permission_helper, "is_student", lambda ctx: False, raising=True)
    monkeypatch.setattr(exam_service, "_require_exam_view_permission", lambda db, ctx, exam: None, raising=True)

    r1 = exam_service.get_exam_questions(db_session, 1, ctx, include_correct_answers=True)

    r2 = exam_service.get_exam_questions(db_session, 1, ctx, include_correct_answers=True)

    assert called["questions"] == 1, f"Expected 1 DB call after caching, got {called['questions']}"

    delete(CACHE_KEYS["exam_questions"].format(1))

    r3 = exam_service.get_exam_questions(db_session, 1, ctx, include_correct_answers=True)

    assert called["questions"] == 2, f"Expected 2 DB calls after cache invalidation, got {called['questions']}"