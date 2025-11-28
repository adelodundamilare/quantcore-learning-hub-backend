import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_teacher_course_assignment_flow(client: TestClient, token_for_role, db_session: Session):
    """
    Test teacher course assignment flow: assign teacher to course, verify visibility, remove teacher.
    """
    print("\n[TEST] Teacher course assignment flow")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    course_title = f"Teacher Assignment Course {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    assert 200 <= r_course.status_code < 300, f"Course creation failed: {r_course.text}"
    course_id = r_course.json().get("data", {}).get("id")
    assert course_id is not None, "No course ID"
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Creating teacher")
    teacher_headers = {"Authorization": f"Bearer {token_for_role('teacher')}"}
    teacher_me = client.get("/account/me", headers=teacher_headers)
    assert teacher_me.status_code == 200, f"Failed to get teacher: {teacher_me.text}"
    teacher_id = teacher_me.json()["data"]["id"]
    print(f"[OK] Teacher created: {teacher_id}")
    
    print("[3] Assigning teacher to course")
    assign_resp = client.post(f"/courses/{course_id}/teachers/{teacher_id}", headers=admin_headers)
    assert 200 <= assign_resp.status_code < 300, f"Teacher assignment failed: {assign_resp.text}"
    print(f"[OK] Teacher assigned to course")
    
    print("[4] Verifying teacher can view course")
    course_get = client.get(f"/courses/{course_id}", headers=teacher_headers)
    assert 200 <= course_get.status_code < 300, f"Teacher cannot view course: {course_get.text}"
    print(f"[OK] Teacher can view course")
    
    print("[5] Verifying course appears in teacher's course list")
    teacher_courses = client.get("/courses/me", headers=teacher_headers)
    assert 200 <= teacher_courses.status_code < 300, f"Failed to get teacher's courses: {teacher_courses.text}"
    course_ids = [c.get("id") for c in teacher_courses.json().get("data", [])]
    assert course_id in course_ids, "Course not in teacher's course list"
    print(f"[OK] Course visible in teacher's course list")
    
    print("[6] Verifying teacher is in course's teacher list")
    teachers_list = client.get(f"/courses/{course_id}/teachers", headers=admin_headers)
    assert 200 <= teachers_list.status_code < 300, f"Failed to get course teachers: {teachers_list.text}"
    teacher_ids = [t.get("id") for t in teachers_list.json().get("data", [])]
    assert teacher_id in teacher_ids, "Teacher not in course's teacher list"
    print(f"[OK] Teacher is in course's teacher list")
    
    print("[7] Removing teacher from course")
    remove_resp = client.delete(f"/courses/{course_id}/teachers/{teacher_id}", headers=admin_headers)
    assert 200 <= remove_resp.status_code < 300, f"Teacher removal failed: {remove_resp.text}"
    print(f"[OK] Teacher removed from course")
    
    print("[7.5] Verifying teacher was removed from course's teacher list")
    teachers_list_verify = client.get(f"/courses/{course_id}/teachers", headers=admin_headers)
    assert 200 <= teachers_list_verify.status_code < 300, f"Failed to get course teachers: {teachers_list_verify.text}"
    teacher_ids_verify = [t.get("id") for t in teachers_list_verify.json().get("data", [])]
    assert teacher_id not in teacher_ids_verify, "Teacher still in course's teacher list after removal"
    print(f"[OK] Teacher confirmed removed from course's teacher list")
    
    print("[8] Verifying teacher can no longer view course")
    course_get_after = client.get(f"/courses/{course_id}", headers=teacher_headers)
    assert course_get_after.status_code == 403, f"Teacher should not be able to view course after removal. Got {course_get_after.status_code}: {course_get_after.text}"
    print(f"[OK] Teacher cannot view course after removal")
    
    print("[9] Verifying course no longer appears in teacher's course list")
    teacher_courses_after = client.get("/courses/me", headers=teacher_headers)
    assert 200 <= teacher_courses_after.status_code < 300, f"Failed to get teacher's courses: {teacher_courses_after.text}"
    course_ids_after = [c.get("id") for c in teacher_courses_after.json().get("data", [])]
    assert course_id not in course_ids_after, "Course still in teacher's course list after removal"
    print(f"[OK] Course removed from teacher's course list")
    
    print("[10] Verifying teacher is no longer in course's teacher list")
    teachers_list_after = client.get(f"/courses/{course_id}/teachers", headers=admin_headers)
    assert 200 <= teachers_list_after.status_code < 300, f"Failed to get course teachers: {teachers_list_after.text}"
    teacher_ids_after = [t.get("id") for t in teachers_list_after.json().get("data", [])]
    assert teacher_id not in teacher_ids_after, "Teacher still in course's teacher list after removal"
    print(f"[OK] Teacher no longer in course's teacher list")
    
    print("[SUCCESS] Complete teacher course assignment flow verified")
