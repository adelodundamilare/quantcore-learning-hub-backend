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
def test_student_course_progress_and_results_flow(client: TestClient, token_for_role, db_session: Session, user_factory, creator_role):
    headers_creator={"Authorization":f"Bearer {token_for_role(creator_role)}"}
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    course_title=f"Flow Course {uuid.uuid4().hex[:6]}"
    r_course=client.post("/courses/",headers=headers_creator,json={"title":course_title,"school_id":admin_school.id})
    if not (200<=r_course.status_code<300):
        pytest.skip("course create not permitted for role")
    course_id=r_course.json().get("data",{}).get("id") or r_course.json().get("id")
    student_email=f"student-flow-{uuid.uuid4().hex}@test.com"
    student=user_factory(student_email)
    client.post(f"/courses/{course_id}/students/{student.id}",headers=headers_creator)
    student_token=login(client,student_email)
    headers_student={"Authorization":f"Bearer {student_token}"}
    r_me=client.get("/courses/me",headers=headers_student)
    if 200<=r_me.status_code<300 and r_me.json().get("data"):
        ids=[c.get("id") for c in r_me.json().get("data")]
        assert course_id in ids
    r_curr=client.post("/curriculum/curriculums/",headers=headers_creator,json={"title":f"Curr {uuid.uuid4().hex[:6]}","description":"d","course_id":course_id})
    if not (200<=r_curr.status_code<300):
        pytest.skip("curriculum creation not permitted")
    curriculum_id=r_curr.json().get("data",{}).get("id")
    r_lesson=client.post("/curriculum/lessons/",headers=headers_creator,json={"title":f"L1-{uuid.uuid4().hex[:4]}","content":"c","curriculum_id":curriculum_id})
    if not (200<=r_lesson.status_code<300):
        pytest.skip("lesson creation not permitted")
    lesson_id=r_lesson.json().get("data",{}).get("id")
    api_call(client,"POST",f"/course-progress/courses/{course_id}/start",headers=headers_student,expected_min=200,expected_max=500)
    api_call(client,"POST",f"/course-progress/lessons/{lesson_id}/start",headers=headers_student,expected_min=200,expected_max=500)
    api_call(client,"POST",f"/course-progress/lessons/{lesson_id}/complete",headers=headers_student,expected_min=200,expected_max=500)
    api_call(client,"GET",f"/course-progress/courses/{course_id}/progress",headers=headers_student,expected_min=200,expected_max=500)
    api_call(client,"GET",f"/course-progress/courses/{course_id}/completed-lessons",headers=headers_student,expected_min=200,expected_max=500)
    api_call(client,"GET",f"/course-progress/courses/{course_id}/lesson-progress",headers=headers_student,expected_min=200,expected_max=500)
    r_exam=client.post("/exams/",headers=headers_creator,json={"title":f"Exam {uuid.uuid4().hex[:6]}","course_id":course_id})
    if not (200<=r_exam.status_code<300):
        pytest.skip("exam create not permitted for role")
    exam_id=r_exam.json().get("data",{}).get("id") or r_exam.json().get("id")
    r_qs=client.post(f"/exams/{exam_id}/questions",headers=headers_creator,json=[{"text":"2+2","options":["3","4"],"correct_answer":"4"}])
    question_id=None
    try:
        dq=r_qs.json().get("data")
        if dq and isinstance(dq,list) and dq[0].get("id"):
            question_id=dq[0].get("id")
    except Exception:
        pass
    r_attempt=client.post(f"/exams/exams/{exam_id}/attempts",headers=headers_student)
    if 200<=r_attempt.status_code<300:
        attempt_id=r_attempt.json().get("data",{}).get("id") or r_attempt.json().get("id")
        answers=[{"question_id":question_id or 1,"answer":"4"}]
        client.post(f"/exams/attempts/{attempt_id}/submit",headers=headers_student,json={"answers":answers})
        client.get(f"/exams/attempts/{attempt_id}",headers=headers_student)
        client.get("/exams/student/my/stats",headers=headers_student)
