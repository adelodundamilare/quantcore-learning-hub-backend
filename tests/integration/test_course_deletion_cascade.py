import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_course_deletion_cascade(client: TestClient, token_for_role, db_session: Session):
    """
    Test course deletion cascades properly.
    Delete course with enrollments, verify enrollments cleaned up, cache invalidated.
    """
    print("\n[TEST] Course deletion cascade")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    course_title = f"Deletion Test Course {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    assert 200 <= r_course.status_code < 300, f"Course creation failed: {r_course.text}"
    course_id = r_course.json().get("data", {}).get("id")
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Creating curriculum and lessons")
    r_curr = client.post(
        "/curriculums/",
        headers=admin_headers,
        json={"title": f"Curr {uuid.uuid4().hex[:6]}", "course_id": course_id}
    )
    assert 200 <= r_curr.status_code < 300
    curriculum_id = r_curr.json().get("data", {}).get("id")
    
    r_lesson = client.post(
        "/lessons/",
        headers=admin_headers,
        json={"title": f"L1-{uuid.uuid4().hex[:4]}", "curriculum_id": curriculum_id, "duration": 30}
    )
    assert 200 <= r_lesson.status_code < 300
    lesson_id = r_lesson.json().get("data", {}).get("id")
    print(f"[OK] Curriculum and lesson created")
    
    print("[3] Enrolling students")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    assert student_me.status_code == 200
    student_id = student_me.json()["data"]["id"]
    
    enroll = client.post(f"/courses/{course_id}/students/{student_id}", headers=admin_headers)
    assert 200 <= enroll.status_code < 300, f"Enrollment failed: {enroll.text}"
    print(f"[OK] Student enrolled")
    
    print("[4] Student starts course and lesson")
    client.post(f"/courses/{course_id}/start", headers=student_headers)
    client.post(f"/lessons/{lesson_id}/start", headers=student_headers)
    print(f"[OK] Student started course and lesson")
    
    print("[5] Verify course and enrollment exist")
    my_courses = client.get("/courses/me", headers=student_headers)
    assert 200 <= my_courses.status_code < 300
    course_ids = [c.get("id") for c in my_courses.json().get("data", [])]
    assert course_id in course_ids, "Course not found in student's courses"
    print(f"[OK] Course exists in student's course list")
    
    print("[6] Delete course")
    delete_course = client.delete(f"/courses/{course_id}", headers=admin_headers)
    assert 200 <= delete_course.status_code < 300, f"Course deletion failed: {delete_course.text}"
    print(f"[OK] Course deleted")
    
    print("[7] Verify course no longer in student's list")
    my_courses_after = client.get("/courses/me", headers=student_headers)
    assert 200 <= my_courses_after.status_code < 300
    course_ids_after = [c.get("id") for c in my_courses_after.json().get("data", [])]
    assert course_id not in course_ids_after, "Course still in student's list after deletion"
    print(f"[OK] Course removed from student's course list")
    
    print("[8] Verify course cannot be accessed directly")
    get_deleted = client.get(f"/courses/{course_id}", headers=student_headers)
    assert get_deleted.status_code == 404, f"Deleted course should return 404, got {get_deleted.status_code}"
    print(f"[OK] Deleted course returns 404")
    
    print("[SUCCESS] Course deletion cascade verified")
