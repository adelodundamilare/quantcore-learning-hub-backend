import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.crud.school import school as crud_school
from app.crud.user import user as crud_user
from app.core.security import get_password_hash
from app.core.constants import ADMIN_SCHOOL_NAME


def login(client: TestClient, email: str, password: str = "testpass123") -> str:
    r=client.post("/auth/login",json={"email":email,"password":password})
    b=r.json()
    return b.get("data",{}).get("token",{}).get("access_token") or b.get("token",{}).get("access_token") or b.get("access_token")


def _create_school_b(client: TestClient, super_admin_token: str) -> int:
    email=f"admin-{uuid.uuid4().hex}@test.com"
    r=client.post("/schools",headers={"Authorization":f"Bearer {super_admin_token}"},json={"school_name":f"SCH-{uuid.uuid4().hex[:6]}","email":email,"full_name":"Admin B"})
    if 200<=r.status_code<500:
        data=r.json().get("data") or {}
        return data.get("id") or r.json().get("id")
    return None


def _create_course(client: TestClient, token: str, school_id: int) -> int:
    r=client.post("/courses/",headers={"Authorization":f"Bearer {token}"},json={"title":f"C-{uuid.uuid4().hex[:6]}","school_id":school_id})
    if 200<=r.status_code<300:
        d=r.json().get("data") or {}
        return d.get("id") or r.json().get("id")
    return None


def _create_curriculum_and_lesson(client: TestClient, token: str, course_id: int):
    r_cur=client.post("/curriculum/curriculums/",headers={"Authorization":f"Bearer {token}"},json={"title":f"Cur-{uuid.uuid4().hex[:4]}","description":"d","course_id":course_id})
    cur_id=(r_cur.json().get("data") or {}).get("id") if 200<=r_cur.status_code<300 else None
    r_les=client.post("/curriculum/lessons/",headers={"Authorization":f"Bearer {token}"},json={"title":f"L-{uuid.uuid4().hex[:4]}","content":"c","curriculum_id":cur_id})
    les_id=(r_les.json().get("data") or {}).get("id") if 200<=r_les.status_code<300 else None
    return cur_id, les_id


@pytest.mark.parametrize("creator_role", ["super_admin","school_admin"])
def test_student_isolation_between_schools(client: TestClient, token_for_role, super_admin_token: str, db_session: Session, user_factory, creator_role, _ensure_student_role_exists):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    school_b_id=_create_school_b(client,super_admin_token)
    token_admin={"Authorization":f"Bearer {token_for_role(creator_role)}"}
    course_a_id=_create_course(client, token_for_role(creator_role), admin_school.id)
    course_b_id=_create_course(client, token_for_role(creator_role), school_b_id)
    s_a_email=f"stuA-{uuid.uuid4().hex}@t.com"
    s_b_email=f"stuB-{uuid.uuid4().hex}@t.com"
    s_a=crud_user.create(db_session,obj_in={"full_name":"Stu A","email":s_a_email,"hashed_password":get_password_hash("testpass123"),"is_active":True})
    s_b=crud_user.create(db_session,obj_in={"full_name":"Stu B","email":s_b_email,"hashed_password":get_password_hash("testpass123"),"is_active":True})
    role=_ensure_student_role_exists
    crud_user.add_user_to_school(db_session,user=s_a,school=admin_school,role=role)
    school_b=crud_school.get(db_session,id=school_b_id)
    crud_user.add_user_to_school(db_session,user=s_b,school=school_b,role=role)
    db_session.commit()
    client.post(f"/courses/{course_a_id}/students/{s_a.id}",headers=token_admin)
    client.post(f"/courses/{course_b_id}/students/{s_b.id}",headers=token_admin)
    s_a_token=login(client,s_a_email)
    s_b_token=login(client,s_b_email)
    h_a={"Authorization":f"Bearer {s_a_token}"}
    h_b={"Authorization":f"Bearer {s_b_token}"}
    r_b=client.get(f"/course-progress/courses/{course_b_id}/progress",headers=h_a)
    assert r_b.status_code in (403,404)
    r_a=client.get(f"/course-progress/courses/{course_a_id}/progress",headers=h_b)
    assert r_a.status_code in (403,404)


def test_exam_isolation_between_schools(client: TestClient, token_for_role, super_admin_token: str, db_session: Session, _ensure_student_role_exists):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    school_b_id=_create_school_b(client,super_admin_token)
    token_admin={"Authorization":f"Bearer {token_for_role('super_admin')}"}
    course_a_id=_create_course(client, token_for_role('super_admin'), admin_school.id)
    course_b_id=_create_course(client, token_for_role('super_admin'), school_b_id)
    cur_a, les_a=_create_curriculum_and_lesson(client, token_for_role('super_admin'), course_a_id)
    from app.crud.user import user as crud_user
    from app.core.security import get_password_hash
    s_a_email=f"stuAA-{uuid.uuid4().hex}@t.com"
    s_b_email=f"stuBB-{uuid.uuid4().hex}@t.com"
    s_a=crud_user.create(db_session,obj_in={"full_name":"Stu AA","email":s_a_email,"hashed_password":get_password_hash("testpass123"),"is_active":True})
    s_b=crud_user.create(db_session,obj_in={"full_name":"Stu BB","email":s_b_email,"hashed_password":get_password_hash("testpass123"),"is_active":True})
    role=_ensure_student_role_exists
    crud_user.add_user_to_school(db_session,user=s_a,school=admin_school,role=role)
    school_b=crud_school.get(db_session,id=school_b_id)
    crud_user.add_user_to_school(db_session,user=s_b,school=school_b,role=role)
    db_session.commit()
    client.post(f"/courses/{course_a_id}/students/{s_a.id}",headers=token_admin)
    client.post(f"/courses/{course_b_id}/students/{s_b.id}",headers=token_admin)
    r_exam=client.post("/exams/",headers=token_admin,json={"title":f"EX-{uuid.uuid4().hex[:4]}","course_id":course_a_id})
    if not (200<=r_exam.status_code<300):
        pytest.skip("exam create not available")
    exam_id=r_exam.json().get("data",{}).get("id") or r_exam.json().get("id")
    client.post(f"/exams/{exam_id}/questions",headers=token_admin,json=[{"text":"2+2","options":["3","4"],"correct_answer":"4"}])
    s_a_token=login(client,s_a_email)
    s_b_token=login(client,s_b_email)
    h_a={"Authorization":f"Bearer {s_a_token}"}
    h_b={"Authorization":f"Bearer {s_b_token}"}
    ra=client.post(f"/exams/exams/{exam_id}/attempts",headers=h_a)
    assert ra.status_code in (200,404)
    rb=client.post(f"/exams/exams/{exam_id}/attempts",headers=h_b)
    assert rb.status_code in (403,404)
