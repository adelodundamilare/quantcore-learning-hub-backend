import uuid
from fastapi.testclient import TestClient


def test_super_admin_invite_student_to_school(client: TestClient, token_for_role, db_session):
    """
    Test super admin inviting a student to their school (admin school).
    Verify student is assigned with student role.
    """
    print("\n[TEST] Super admin invite student")
    
    from app.crud.school import school as crud_school
    from app.core.constants import ADMIN_SCHOOL_NAME
    
    super_admin_token = token_for_role('super_admin')
    super_admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    print(f"[OK] Admin school found: {admin_school.id}")
    
    print("[1] Inviting student to admin school")
    student_email = f"student-{uuid.uuid4()}@test.com"
    invite_response = client.post(
        "/account/invite",
        headers=super_admin_headers,
        json={
            "email": student_email,
            "full_name": "Test Student",
            "role_name": "student"
        }
    )
    assert 200 <= invite_response.status_code < 300, f"Student invitation failed: {invite_response.text}"
    student_id = invite_response.json().get("data", {}).get("id")
    assert student_id is not None, "Student ID not returned"
    print(f"[OK] Student invited: {student_id}")
    
    print("[2] Verifying student is in admin school's student list")
    students_response = client.get(
        f"/schools/{admin_school.id}/students",
        headers=super_admin_headers
    )
    assert students_response.status_code == 200, f"Failed to get school students: {students_response.text}"
    students = students_response.json().get("data", [])
    student_ids = [s.get("id") for s in students]
    assert student_id in student_ids, f"Invited student {student_id} not found in school's student list"
    print(f"[OK] Student verified in admin school")
    
    print("[SUCCESS] Super admin student invitation verified")


def test_super_admin_invite_teacher_to_school(client: TestClient, token_for_role, db_session):
    """
    Test super admin inviting a teacher to their school (admin school).
    Verify teacher is assigned with teacher role.
    """
    print("\n[TEST] Super admin invite teacher")
    
    from app.crud.school import school as crud_school
    from app.core.constants import ADMIN_SCHOOL_NAME
    
    super_admin_token = token_for_role('super_admin')
    super_admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    print(f"[OK] Admin school found: {admin_school.id}")
    
    print("[1] Inviting teacher to admin school")
    teacher_email = f"teacher-{uuid.uuid4()}@test.com"
    invite_response = client.post(
        "/account/invite",
        headers=super_admin_headers,
        json={
            "email": teacher_email,
            "full_name": "Test Teacher",
            "role_name": "teacher"
        }
    )
    assert 200 <= invite_response.status_code < 300, f"Teacher invitation failed: {invite_response.text}"
    teacher_id = invite_response.json().get("data", {}).get("id")
    assert teacher_id is not None, "Teacher ID not returned"
    print(f"[OK] Teacher invited: {teacher_id}")
    
    print("[2] Verifying teacher is in admin school's teacher list")
    teachers_response = client.get(
        f"/schools/{admin_school.id}/teachers",
        headers=super_admin_headers
    )
    assert teachers_response.status_code == 200, f"Failed to get school teachers: {teachers_response.text}"
    teachers = teachers_response.json().get("data", [])
    teacher_ids = [t.get("id") for t in teachers]
    assert teacher_id in teacher_ids, f"Invited teacher {teacher_id} not found in school's teacher list"
    print(f"[OK] Teacher verified in admin school")
    
    print("[SUCCESS] Super admin teacher invitation verified")


def test_super_admin_invite_multiple_users(client: TestClient, token_for_role, db_session):
    """
    Test super admin inviting multiple users (students and teachers) to their school (admin school).
    Verify all users are properly assigned with correct roles.
    """
    print("\n[TEST] Super admin invite multiple users")
    
    from app.crud.school import school as crud_school
    from app.core.constants import ADMIN_SCHOOL_NAME
    
    super_admin_token = token_for_role('super_admin')
    super_admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    print(f"[OK] Admin school found: {admin_school.id}")
    
    print("[1] Inviting 3 students to admin school")
    student_ids = []
    for i in range(3):
        student_email = f"student-{uuid.uuid4()}@test.com"
        invite_response = client.post(
            "/account/invite",
            headers=super_admin_headers,
            json={
                "email": student_email,
                "full_name": f"Student {i+1}",
                "role_name": "student"
            }
        )
        assert 200 <= invite_response.status_code < 300, f"Student {i+1} invitation failed: {invite_response.text}"
        student_id = invite_response.json().get("data", {}).get("id")
        assert student_id is not None, f"Student {i+1} ID not returned"
        student_ids.append(student_id)
    print(f"[OK] 3 students invited successfully")
    
    print("[2] Inviting 2 teachers to admin school")
    teacher_ids = []
    for i in range(2):
        teacher_email = f"teacher-{uuid.uuid4()}@test.com"
        invite_response = client.post(
            "/account/invite",
            headers=super_admin_headers,
            json={
                "email": teacher_email,
                "full_name": f"Teacher {i+1}",
                "role_name": "teacher"
            }
        )
        assert 200 <= invite_response.status_code < 300, f"Teacher {i+1} invitation failed: {invite_response.text}"
        teacher_id = invite_response.json().get("data", {}).get("id")
        assert teacher_id is not None, f"Teacher {i+1} ID not returned"
        teacher_ids.append(teacher_id)
    print(f"[OK] 2 teachers invited successfully")
    
    print("[3] Verifying all students are in admin school's student list")
    students_response = client.get(
        f"/schools/{admin_school.id}/students",
        headers=super_admin_headers
    )
    assert students_response.status_code == 200, f"Failed to get school students: {students_response.text}"
    school_students = students_response.json().get("data", [])
    school_student_ids = [s.get("id") for s in school_students]
    for student_id in student_ids:
        assert student_id in school_student_ids, f"Student {student_id} not found in admin school"
    print(f"[OK] All 3 students verified in admin school")
    
    print("[4] Verifying all teachers are in admin school's teacher list")
    teachers_response = client.get(
        f"/schools/{admin_school.id}/teachers",
        headers=super_admin_headers
    )
    assert teachers_response.status_code == 200, f"Failed to get school teachers: {teachers_response.text}"
    school_teachers = teachers_response.json().get("data", [])
    school_teacher_ids = [t.get("id") for t in school_teachers]
    for teacher_id in teacher_ids:
        assert teacher_id in school_teacher_ids, f"Teacher {teacher_id} not found in admin school"
    print(f"[OK] All 2 teachers verified in admin school")
    
    print("[SUCCESS] Super admin multiple user invitation verified")
