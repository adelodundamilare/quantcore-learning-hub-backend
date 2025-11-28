import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_curriculum_lesson_deletion(client: TestClient, token_for_role, db_session: Session):
    """
    Test deleting curriculum/lessons with student progress.
    Create lessons with student progress, delete curriculum, verify cascade.
    """
    print("\n[TEST] Curriculum and lesson deletion with progress")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    
    print("[1] Creating course")
    course_title = f"Deletion Cascade {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    course_id = r_course.json().get("data", {}).get("id")
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Creating curriculum with lessons")
    r_curr = client.post(
        "/curriculums/",
        headers=admin_headers,
        json={"title": f"Curr {uuid.uuid4().hex[:6]}", "course_id": course_id}
    )
    curriculum_id = r_curr.json().get("data", {}).get("id")
    
    r_lesson1 = client.post(
        "/lessons/",
        headers=admin_headers,
        json={"title": f"Lesson 1", "curriculum_id": curriculum_id, "duration": 30}
    )
    lesson1_id = r_lesson1.json().get("data", {}).get("id")
    
    r_lesson2 = client.post(
        "/lessons/",
        headers=admin_headers,
        json={"title": f"Lesson 2", "curriculum_id": curriculum_id, "duration": 30}
    )
    lesson2_id = r_lesson2.json().get("data", {}).get("id")
    print(f"[OK] Curriculum created with 2 lessons")
    
    print("[3] Enrolling student and creating progress")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    student_id = student_me.json()["data"]["id"]
    
    client.post(f"/courses/{course_id}/students/{student_id}", headers=admin_headers)
    client.post(f"/courses/{course_id}/start", headers=student_headers)
    client.post(f"/lessons/{lesson1_id}/start", headers=student_headers)
    client.post(f"/lessons/{lesson1_id}/complete", headers=student_headers)
    print(f"[OK] Student created progress on lesson 1")
    
    print("[4] Verify lesson is completed")
    completed = client.get(f"/courses/{course_id}/completed-lessons", headers=student_headers)
    assert 200 <= completed.status_code < 300
    completed_ids = completed.json().get("data", [])
    assert lesson1_id in completed_ids, "Lesson 1 not in completed lessons"
    print(f"[OK] Lesson 1 in completed list")
    
    print("[5] Delete curriculum")
    delete_curr = client.delete(f"/curriculums/{curriculum_id}", headers=admin_headers)
    assert 200 <= delete_curr.status_code < 300, f"Curriculum deletion failed: {delete_curr.text}"
    print(f"[OK] Curriculum deleted")
    
    print("[6] Verify lessons no longer accessible")
    get_lesson = client.get(f"/lessons/{lesson1_id}", headers=student_headers)
    assert get_lesson.status_code == 404, "Deleted lesson should return 404"
    print(f"[OK] Lessons deleted with curriculum")
    
    print("[7] Verify completed lessons list is updated")
    completed_after = client.get(f"/courses/{course_id}/completed-lessons", headers=student_headers)
    assert 200 <= completed_after.status_code < 300
    completed_ids_after = completed_after.json().get("data", [])
    assert lesson1_id not in completed_ids_after, "Deleted lesson still in completed list"
    print(f"[OK] Completed lessons list updated")
    
    print("[SUCCESS] Curriculum lesson deletion cascade verified")
