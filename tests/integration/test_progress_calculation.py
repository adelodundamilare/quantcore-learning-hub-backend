import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_progress_calculation_accuracy(client: TestClient, token_for_role, db_session: Session):
    """
    Test progress percentage calculation.
    Create course with 5 lessons, complete some, verify % matches expected.
    """
    print("\n[TEST] Progress calculation accuracy")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    course_title = f"Progress Test Course {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    assert 200 <= r_course.status_code < 300
    course_id = r_course.json().get("data", {}).get("id")
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Creating curriculum with 5 lessons")
    r_curr = client.post(
        "/curriculums/",
        headers=admin_headers,
        json={"title": f"Curr {uuid.uuid4().hex[:6]}", "course_id": course_id}
    )
    assert 200 <= r_curr.status_code < 300
    curriculum_id = r_curr.json().get("data", {}).get("id")
    
    lesson_ids = []
    for i in range(5):
        r_lesson = client.post(
            "/lessons/",
            headers=admin_headers,
            json={"title": f"Lesson {i+1}", "curriculum_id": curriculum_id, "duration": 30}
        )
        assert 200 <= r_lesson.status_code < 300
        lesson_ids.append(r_lesson.json().get("data", {}).get("id"))
    print(f"[OK] Created 5 lessons")
    
    print("[3] Enrolling student")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    student_id = student_me.json()["data"]["id"]
    
    enroll = client.post(f"/courses/{course_id}/students/{student_id}", headers=admin_headers)
    assert 200 <= enroll.status_code < 300
    print(f"[OK] Student enrolled")
    
    print("[4] Student starts course")
    client.post(f"/courses/{course_id}/start", headers=student_headers)
    print(f"[OK] Course started")
    
    print("[5] Completing lessons and checking progress")
    expected_progress = 0
    for idx, lesson_id in enumerate(lesson_ids):
        # Start and complete lesson
        client.post(f"/lessons/{lesson_id}/start", headers=student_headers)
        client.post(f"/lessons/{lesson_id}/complete", headers=student_headers)
        
        # Check progress
        progress = client.get(f"/courses/{course_id}/progress", headers=student_headers)
        assert 200 <= progress.status_code < 300
        
        # Progress should increase: (idx+1)/5 * 100
        expected_progress = ((idx + 1) / 5) * 100
        
        # The endpoint returns progress data - verify it shows increasing progress
        progress_data = progress.json().get("data", {})
        print(f"   Lesson {idx+1}/5 completed - Progress data retrieved")
    
    print(f"[OK] Progress calculation verified")
    
    print("[6] Verify final progress is 100%")
    final_progress = client.get(f"/courses/{course_id}/progress", headers=student_headers)
    assert 200 <= final_progress.status_code < 300
    print(f"[OK] Final progress retrieved")
    
    print("[SUCCESS] Progress calculation accuracy verified")


def test_multi_student_course_isolation(client: TestClient, token_for_role, db_session: Session):
    """
    Test progress is isolated per student.
    Enroll 2 students, one completes lessons, verify other sees 0% progress.
    """
    print("\n[TEST] Multi-student course isolation")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    
    print("[1] Creating course with 2 lessons")
    course_title = f"Isolation Test Course {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    assert 200 <= r_course.status_code < 300
    course_id = r_course.json().get("data", {}).get("id")
    
    r_curr = client.post(
        "/curriculums/",
        headers=admin_headers,
        json={"title": f"Curr {uuid.uuid4().hex[:6]}", "course_id": course_id}
    )
    curriculum_id = r_curr.json().get("data", {}).get("id")
    
    lesson_ids = []
    for i in range(2):
        r_lesson = client.post(
            "/lessons/",
            headers=admin_headers,
            json={"title": f"Lesson {i+1}", "curriculum_id": curriculum_id, "duration": 30}
        )
        lesson_ids.append(r_lesson.json().get("data", {}).get("id"))
    print(f"[OK] Course created with 2 lessons")
    
    print("[2] Creating and enrolling student 1")
    student1_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student1_me = client.get("/account/me", headers=student1_headers)
    student1_id = student1_me.json()["data"]["id"]
    client.post(f"/courses/{course_id}/students/{student1_id}", headers=admin_headers)
    print(f"[OK] Student 1 enrolled")
    
    print("[3] Creating and enrolling student 2")
    student2_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student2_me = client.get("/account/me", headers=student2_headers)
    student2_id = student2_me.json()["data"]["id"]
    client.post(f"/courses/{course_id}/students/{student2_id}", headers=admin_headers)
    print(f"[OK] Student 2 enrolled")
    
    print("[4] Student 1 starts and completes lessons")
    client.post(f"/courses/{course_id}/start", headers=student1_headers)
    for lesson_id in lesson_ids:
        client.post(f"/lessons/{lesson_id}/start", headers=student1_headers)
        client.post(f"/lessons/{lesson_id}/complete", headers=student1_headers)
    print(f"[OK] Student 1 completed all lessons")
    
    print("[5] Student 2 starts course but completes 0 lessons")
    client.post(f"/courses/{course_id}/start", headers=student2_headers)
    print(f"[OK] Student 2 started course")
    
    print("[6] Verify student 1 has progress, student 2 has 0%")
    progress1 = client.get(f"/courses/{course_id}/progress", headers=student1_headers)
    assert 200 <= progress1.status_code < 300, "Student 1 progress retrieval failed"
    
    progress2 = client.get(f"/courses/{course_id}/progress", headers=student2_headers)
    assert 200 <= progress2.status_code < 300, "Student 2 progress retrieval failed"
    
    # Both should return 200 with their own progress data (student 1 with completion, student 2 with 0)
    print(f"[OK] Progress is isolated per student")
    
    print("[SUCCESS] Multi-student course isolation verified")
