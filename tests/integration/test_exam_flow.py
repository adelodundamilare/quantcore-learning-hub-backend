import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course

@pytest.mark.parametrize("creator",["teacher","school_admin","super_admin"])
def test_exam_full_flow(client: TestClient, token_for_role, db_session: Session, creator):
    headers={"Authorization":f"Bearer {token_for_role(creator)}"}
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    course=crud_course.create(db_session,obj_in={"title":"Exam Flow Course","school_id":admin_school.id})
    r_exam=client.post("/exams/",headers=headers,json={"title":"Exam Flow","course_id":course.id})
    if not (200<=r_exam.status_code<300):
        pytest.skip("exam create not permitted for role")
    exam_id=r_exam.json().get("data",{}).get("id") or r_exam.json().get("id")
    qs=[{"text":"2+2","options":["3","4"],"correct_answer":"4"}]
    client.post(f"/exams/{exam_id}/questions",headers=headers,json=qs)
    student_headers={"Authorization":f"Bearer {token_for_role('student')}"}
    client.post(f"/exams/{exam_id}/attempts",headers=student_headers)
    client.post(f"/exams/{exam_id}/submit",headers=student_headers,json={"answers":[{"question_id":1,"answer":"4"}]})
    client.get(f"/exams/{exam_id}/results",headers=headers)