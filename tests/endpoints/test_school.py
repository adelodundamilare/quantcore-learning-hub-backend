import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.core.security import get_password_hash

ENDPOINTS_PUBLIC=[
    ("GET","/schools/admin/schools"),
    ("GET","/schools/admin/schools/report"),
]

@pytest.mark.parametrize("method,path",ENDPOINTS_PUBLIC,ids=[f"{m} {p}" for m,p in ENDPOINTS_PUBLIC])
def test_school_admin_smoke(client: TestClient, super_admin_token: str, method, path):
    headers={"Authorization":f"Bearer {super_admin_token}"}
    api_call(client,method,path,headers=headers,expected_min=200,expected_max=500)

def test_create_update_delete_school_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers={"Authorization":f"Bearer {super_admin_token}"}
    unique_email=f"school-admin-{uuid.uuid4()}@test.com"
    api_call(client,"POST","/schools",headers=headers,json={"school_name":"New School","admin_email":unique_email,"admin_full_name":"Test Admin"},expected_min=200,expected_max=500)
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    api_call(client,"PUT",f"/schools/admin/schools/{admin_school.id}",headers=headers,json={"name":"Updated School Name"},expected_min=200,expected_max=500)


def test_read_school_smoke(client: TestClient, db_session: Session, _ensure_admin_school_exists):
    admin_school=_ensure_admin_school_exists
    api_call(client,"GET",f"/schools/{admin_school.id}",expected_min=200,expected_max=300)


from app.crud.user import user as crud_user

def test_school_students_teachers_smoke(client: TestClient, super_admin_token: str, db_session: Session, _ensure_admin_school_exists, _ensure_student_role_exists, _ensure_teacher_role_exists):
    admin_school=_ensure_admin_school_exists
    student_role=_ensure_student_role_exists
    teacher_role=_ensure_teacher_role_exists
    s=crud_user.create(db_session,obj_in={"full_name":"S","email":f"s-{uuid.uuid4().hex}@t.com","hashed_password":get_password_hash("testpass123"),"is_active":True})
    crud_user.add_user_to_school(db_session,user=s,school=admin_school,role=student_role)
    t=crud_user.create(db_session,obj_in={"full_name":"T","email":f"t-{uuid.uuid4().hex}@t.com","hashed_password":get_password_hash("testpass123"),"is_active":True})
    crud_user.add_user_to_school(db_session,user=t,school=admin_school,role=teacher_role)
    db_session.commit()
    headers={"Authorization":f"Bearer {super_admin_token}"}
    api_call(client,"GET",f"/schools/{admin_school.id}/students",headers=headers,expected_min=200,expected_max=500)
    api_call(client,"GET",f"/schools/{admin_school.id}/teachers",headers=headers,expected_min=200,expected_max=500)
