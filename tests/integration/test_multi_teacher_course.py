import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_multi_teacher_course(client: TestClient, token_for_role, db_session: Session):
    """
    Test multiple teachers on same course with different permissions.
    Ensure all teachers can view/modify course content.
    """
    print("\n[TEST] Multiple teachers on same course")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    course_title = f"Multi Teacher Course {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    assert 200 <= r_course.status_code < 300, f"Course creation failed: {r_course.text}"
    course_id = r_course.json().get("data", {}).get("id")
    assert course_id is not None, "No course ID"
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Creating first teacher")
    teacher1_headers = {"Authorization": f"Bearer {token_for_role('teacher')}"}
    teacher1_me = client.get("/account/me", headers=teacher1_headers)
    assert teacher1_me.status_code == 200
    teacher1_id = teacher1_me.json()["data"]["id"]
    print(f"[OK] Teacher 1 created: {teacher1_id}")
    
    print("[3] Creating second teacher")
    teacher2_headers = {"Authorization": f"Bearer {token_for_role('teacher')}"}
    teacher2_me = client.get("/account/me", headers=teacher2_headers)
    assert teacher2_me.status_code == 200
    teacher2_id = teacher2_me.json()["data"]["id"]
    print(f"[OK] Teacher 2 created: {teacher2_id}")
    
    print("[4] Assigning first teacher to course")
    assign1 = client.post(f"/courses/{course_id}/teachers/{teacher1_id}", headers=admin_headers)
    assert 200 <= assign1.status_code < 300, f"Teacher 1 assignment failed: {assign1.text}"
    print(f"[OK] Teacher 1 assigned")
    
    print("[5] Assigning second teacher to course")
    assign2 = client.post(f"/courses/{course_id}/teachers/{teacher2_id}", headers=admin_headers)
    assert 200 <= assign2.status_code < 300, f"Teacher 2 assignment failed: {assign2.text}"
    print(f"[OK] Teacher 2 assigned")
    
    print("[6] Verifying both teachers see the course")
    course1 = client.get(f"/courses/{course_id}", headers=teacher1_headers)
    assert 200 <= course1.status_code < 300, f"Teacher 1 cannot view course: {course1.text}"
    course2 = client.get(f"/courses/{course_id}", headers=teacher2_headers)
    assert 200 <= course2.status_code < 300, f"Teacher 2 cannot view course: {course2.text}"
    print(f"[OK] Both teachers can view course")
    
    print("[7] Verifying both teachers in course's teacher list")
    teachers_list = client.get(f"/courses/{course_id}/teachers", headers=admin_headers)
    assert 200 <= teachers_list.status_code < 300
    teacher_ids = [t.get("id") for t in teachers_list.json().get("data", [])]
    assert teacher1_id in teacher_ids, "Teacher 1 not in course's teacher list"
    assert teacher2_id in teacher_ids, "Teacher 2 not in course's teacher list"
    print(f"[OK] Both teachers in course's teacher list")
    
    print("[8] Teacher 1 creates curriculum")
    r_curr = client.post(
        "/curriculums/",
        headers=teacher1_headers,
        json={"title": f"Curr {uuid.uuid4().hex[:6]}", "course_id": course_id}
    )
    assert 200 <= r_curr.status_code < 300, f"Curriculum creation failed: {r_curr.text}"
    curriculum_id = r_curr.json().get("data", {}).get("id")
    print(f"[OK] Curriculum created: {curriculum_id}")
    
    print("[9] Teacher 2 creates lesson in same curriculum")
    r_lesson = client.post(
        "/lessons/",
        headers=teacher2_headers,
        json={"title": f"L1-{uuid.uuid4().hex[:4]}", "curriculum_id": curriculum_id, "duration": 30}
    )
    assert 200 <= r_lesson.status_code < 300, f"Lesson creation failed: {r_lesson.text}"
    lesson_id = r_lesson.json().get("data", {}).get("id")
    print(f"[OK] Lesson created by teacher 2: {lesson_id}")
    
    print("[10] Verify curriculum appears in both teachers' courses")
    my_courses1 = client.get("/courses/me", headers=teacher1_headers)
    assert 200 <= my_courses1.status_code < 300
    courses1 = my_courses1.json().get("data", [])
    my_course1 = next((c for c in courses1 if c.get("id") == course_id), None)
    assert my_course1 is not None, "Course not in teacher 1's courses"
    
    my_courses2 = client.get("/courses/me", headers=teacher2_headers)
    assert 200 <= my_courses2.status_code < 300
    courses2 = my_courses2.json().get("data", [])
    my_course2 = next((c for c in courses2 if c.get("id") == course_id), None)
    assert my_course2 is not None, "Course not in teacher 2's courses"
    print(f"[OK] Course visible to both teachers")
    
    print("[SUCCESS] Multiple teachers on same course verified")
