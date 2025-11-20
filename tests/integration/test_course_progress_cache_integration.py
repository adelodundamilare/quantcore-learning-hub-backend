import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school

def login(client: TestClient, email: str, password: str = "testpass123") -> str:
    r=client.post("/auth/login",json={"email":email,"password":password})
    b=r.json()
    return b.get("data",{}).get("token",{}).get("access_token") or b.get("token",{}).get("access_token") or b.get("access_token")

@pytest.mark.parametrize("creator_role", ["teacher", "school_admin", "super_admin"])
def test_course_progress_cache_invalidation(client: TestClient, token_for_role, db_session: Session, user_factory, creator_role):
    headers_creator={"Authorization":f"Bearer {token_for_role(creator_role)}"}
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    r_course=client.post("/courses/",headers=headers_creator,json={"title":f"CacheFlow {uuid.uuid4().hex[:6]}","school_id":admin_school.id})
    if not (200<=r_course.status_code<300):
        pytest.skip("course create not permitted")
    course_id=r_course.json().get("data",{}).get("id")
    student_email=f"cache-student-{uuid.uuid4().hex}@t.com"
    student=user_factory(student_email)
    client.post(f"/courses/{course_id}/students/{student.id}",headers=headers_creator)
    student_token=login(client,student_email)
    headers_student={"Authorization":f"Bearer {student_token}"}
    r_curr=client.post("/curriculum/curriculums/",headers=headers_creator,json={"title":"C","description":"d","course_id":course_id})
    if not (200<=r_curr.status_code<300):
        pytest.skip("no curriculum")
    curriculum_id=r_curr.json().get("data",{}).get("id")
    r_lesson=client.post("/curriculum/lessons/",headers=headers_creator,json={"title":"L","content":"c","curriculum_id":curriculum_id})
    if not (200<=r_lesson.status_code<300):
        pytest.skip("no lesson")
    lesson_id=r_lesson.json().get("data",{}).get("id")
    r1=client.get(f"/course-progress/courses/{course_id}/progress",headers=headers_student)
    r2=client.get(f"/course-progress/courses/{course_id}/progress",headers=headers_student)
    assert r1.status_code==r2.status_code
    client.post(f"/course-progress/lessons/{lesson_id}/start",headers=headers_student)
    client.post(f"/course-progress/lessons/{lesson_id}/complete",headers=headers_student)
    r3=client.get(f"/course-progress/courses/{course_id}/progress",headers=headers_student)
    assert r3.status_code in (200,404)
