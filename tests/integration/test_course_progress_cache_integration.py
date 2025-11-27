import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school

def test_course_progress_cache_invalidation(client: TestClient, token_for_role, db_session: Session):
    """
    Test that cache is properly invalidated during complete course progress flow.
    Covers: course creation, curriculum creation, lesson creation, enrollment,
    course start, lesson start, lesson completion, and progress endpoint updates.
    """
    creator_role = "teacher"
    print(f"\n[TEST] Cache invalidation - complete course progress flow")
    
    headers_creator = {"Authorization": f"Bearer {token_for_role(creator_role)}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    r_course = client.post(
        "/courses/",
        headers=headers_creator,
        json={"title": f"CacheTest", "school_id": admin_school.id}
    )
    assert 200 <= r_course.status_code < 300, f"Course creation failed: {r_course.text}"
    course_id = r_course.json().get("data", {}).get("id")
    assert course_id is not None, "No course ID"
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Getting student token")
    student_token = token_for_role("student")
    headers_student = {"Authorization": f"Bearer {student_token}"}
    
    me_resp = client.get("/account/me", headers=headers_student)
    assert me_resp.status_code == 200, f"Failed to get student info: {me_resp.text}"
    student_id = me_resp.json()["data"]["id"]
    print(f"[OK] Student authenticated: {student_id}")
    
    print("[3] Enrolling student in course")
    enroll_resp = client.post(
        f"/courses/{course_id}/students/{student_id}",
        headers=headers_creator
    )
    assert 200 <= enroll_resp.status_code < 300, f"Enrollment failed: {enroll_resp.text}"
    print(f"[OK] Student enrolled")
    
    print("[4] Verifying course endpoint works")
    courses_resp = client.get("/courses/me", headers=headers_student)
    assert 200 <= courses_resp.status_code < 300, f"Courses endpoint failed: {courses_resp.text}"
    print(f"[OK] Courses endpoint working")
    
    print("[5] Creating curriculum")
    curr_resp = client.post(
        "/curriculums/",
        headers=headers_creator,
        json={"title": "Test Curriculum", "course_id": course_id}
    )
    assert 200 <= curr_resp.status_code < 300, f"Curriculum creation failed: {curr_resp.text}"
    curriculum_id = curr_resp.json().get("data", {}).get("id")
    assert curriculum_id is not None, "No curriculum ID"
    print(f"[OK] Curriculum created: {curriculum_id}")
    
    print("[6] Creating lesson")
    lesson_resp = client.post(
        "/lessons/",
        headers=headers_creator,
        json={"title": "Test Lesson", "curriculum_id": curriculum_id, "duration": 30}
    )
    assert 200 <= lesson_resp.status_code < 300, f"Lesson creation failed: {lesson_resp.text}"
    lesson_id = lesson_resp.json().get("data", {}).get("id")
    assert lesson_id is not None, "No lesson ID"
    print(f"[OK] Lesson created: {lesson_id}")
    
    print("[7] Starting course (invalidates cache)")
    start_course_resp = client.post(
        f"/courses/{course_id}/start",
        headers=headers_student
    )
    assert 200 <= start_course_resp.status_code < 300, f"Start course failed: {start_course_resp.text}"
    print(f"[OK] Course started")
    
    print("[8] Verifying course progress endpoint after start")
    progress_resp = client.get(
        f"/courses/{course_id}/progress",
        headers=headers_student
    )
    assert 200 <= progress_resp.status_code < 300, f"Progress endpoint failed: {progress_resp.text}"
    progress_data = progress_resp.json().get("data", {})
    assert progress_data.get("status") == "in_progress", f"Course status should be in_progress but got {progress_data.get('status')}"
    assert progress_data.get("started_at") is not None, "Course should have started_at set"
    print(f"[OK] Course progress retrieved with correct status")
    
    print("[9] Starting lesson (invalidates cache)")
    start_lesson_resp = client.post(
        f"/lessons/{lesson_id}/start",
        headers=headers_student
    )
    assert 200 <= start_lesson_resp.status_code < 300, f"Start lesson failed: {start_lesson_resp.text}"
    print(f"[OK] Lesson started")
    
    print("[10] Verifying lesson progress endpoint after start")
    lesson_progress_resp = client.get(
        f"/courses/{course_id}/lesson-progress",
        headers=headers_student
    )
    assert 200 <= lesson_progress_resp.status_code < 300, f"Lesson progress endpoint failed: {lesson_progress_resp.text}"
    lesson_progress_list = lesson_progress_resp.json().get("data", [])
    assert len(lesson_progress_list) > 0, "No lesson progress found"
    lesson = lesson_progress_list[0]
    assert lesson.get("started_at") is not None, "Lesson should have started_at set"
    assert lesson.get("is_completed") == False, "Lesson should not be completed yet"
    print(f"[OK] Lesson progress retrieved with correct status")
    
    print("[11] Completing lesson (invalidates cache)")
    complete_lesson_resp = client.post(
        f"/lessons/{lesson_id}/complete",
        headers=headers_student
    )
    assert 200 <= complete_lesson_resp.status_code < 300, f"Complete lesson failed: {complete_lesson_resp.text}"
    print(f"[OK] Lesson completed")
    
    print("[12] Verifying completed lessons endpoint after completion")
    completed_resp = client.get(
        f"/courses/{course_id}/completed-lessons",
        headers=headers_student
    )
    assert 200 <= completed_resp.status_code < 300, f"Completed lessons endpoint failed: {completed_resp.text}"
    completed_lessons = completed_resp.json().get("data", [])
    assert lesson_id in completed_lessons, f"Lesson {lesson_id} should be in completed lessons"
    print(f"[OK] Lesson found in completed lessons after cache invalidation")
    
    print(f"[SUCCESS] Complete course progress cache invalidation flow verified")
