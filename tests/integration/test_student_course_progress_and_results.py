import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_student_course_progress_and_results_flow(client: TestClient, token_for_role, db_session: Session):
    """
    Test complete student course progress and exam results flow:
    - Create course, curriculum, lessons
    - Start course and lessons, complete lessons
    - Verify progress tracking
    - Create exam, submit answers
    - Verify exam attempt and stats
    """
    print("\n[TEST] Student course progress and results flow")
    
    headers_creator = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    course_title = f"Flow Course {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=headers_creator, json={"title": course_title, "school_id": admin_school.id})
    assert 200 <= r_course.status_code < 300, f"Course creation failed: {r_course.text}"
    course_id = r_course.json().get("data", {}).get("id")
    assert course_id is not None, "No course ID"
    print(f"[OK] Course created: {course_id}")
    
    print("[2] Creating student and enrolling in course")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    assert student_me.status_code == 200, f"Failed to get student: {student_me.text}"
    student_id = student_me.json()["data"]["id"]
    
    enroll_resp = client.post(f"/courses/{course_id}/students/{student_id}", headers=headers_creator)
    assert 200 <= enroll_resp.status_code < 300, f"Enrollment failed: {enroll_resp.text}"
    print(f"[OK] Student enrolled in course")
    
    print("[3] Verifying student sees course in their list")
    my_courses = client.get("/courses/me", headers=student_headers)
    assert 200 <= my_courses.status_code < 300, f"Failed to get student courses: {my_courses.text}"
    course_ids = [c.get("id") for c in my_courses.json().get("data", [])]
    assert course_id in course_ids, "Course not in student's course list"
    print(f"[OK] Course visible in student's course list")
    
    print("[4] Creating curriculum")
    r_curr = client.post(
        "/curriculums/",
        headers=headers_creator,
        json={"title": f"Curr {uuid.uuid4().hex[:6]}", "course_id": course_id}
    )
    assert 200 <= r_curr.status_code < 300, f"Curriculum creation failed: {r_curr.text}"
    curriculum_id = r_curr.json().get("data", {}).get("id")
    assert curriculum_id is not None, "No curriculum ID"
    print(f"[OK] Curriculum created: {curriculum_id}")
    
    print("[5] Creating lesson")
    r_lesson = client.post(
        "/lessons/",
        headers=headers_creator,
        json={"title": f"L1-{uuid.uuid4().hex[:4]}", "curriculum_id": curriculum_id, "duration": 30}
    )
    assert 200 <= r_lesson.status_code < 300, f"Lesson creation failed: {r_lesson.text}"
    lesson_id = r_lesson.json().get("data", {}).get("id")
    assert lesson_id is not None, "No lesson ID"
    print(f"[OK] Lesson created: {lesson_id}")
    
    print("[6] Starting course")
    start_course = client.post(f"/courses/{course_id}/start", headers=student_headers)
    assert 200 <= start_course.status_code < 300, f"Start course failed: {start_course.text}"
    print(f"[OK] Course started")
    
    print("[7] Starting lesson")
    start_lesson = client.post(f"/lessons/{lesson_id}/start", headers=student_headers)
    assert 200 <= start_lesson.status_code < 300, f"Start lesson failed: {start_lesson.text}"
    print(f"[OK] Lesson started")
    
    print("[8] Completing lesson")
    complete_lesson = client.post(f"/lessons/{lesson_id}/complete", headers=student_headers)
    assert 200 <= complete_lesson.status_code < 300, f"Complete lesson failed: {complete_lesson.text}"
    print(f"[OK] Lesson completed")
    
    print("[9] Verifying course progress")
    progress = client.get(f"/courses/{course_id}/progress", headers=student_headers)
    assert 200 <= progress.status_code < 300, f"Get progress failed: {progress.text}"
    print(f"[OK] Course progress retrieved")
    
    print("[10] Getting completed lessons list")
    completed = client.get(f"/courses/{course_id}/completed-lessons", headers=student_headers)
    assert 200 <= completed.status_code < 300, f"Get completed lessons failed: {completed.text}"
    completed_ids = completed.json().get("data", [])
    assert lesson_id in completed_ids, "Lesson not in completed list"
    print(f"[OK] Lesson in completed lessons")
    
    print("[11] Getting lesson progress details")
    lesson_prog = client.get(f"/courses/{course_id}/lesson-progress", headers=student_headers)
    assert 200 <= lesson_prog.status_code < 300, f"Get lesson progress failed: {lesson_prog.text}"
    print(f"[OK] Lesson progress details retrieved")
    
    print("[12] Creating exam")
    r_exam = client.post("/exams/", headers=headers_creator, json={"title": f"Exam {uuid.uuid4().hex[:6]}", "course_id": course_id})
    assert 200 <= r_exam.status_code < 300, f"Exam creation failed: {r_exam.text}"
    exam_id = r_exam.json().get("data", {}).get("id")
    assert exam_id is not None, "No exam ID"
    print(f"[OK] Exam created: {exam_id}")
    
    print("[13] Adding question to exam")
    r_qs = client.post(
        f"/exams/{exam_id}/questions",
        headers=headers_creator,
        json=[{
            "exam_id": exam_id,
            "question_text": "What is 2+2?",
            "question_type": "multiple_choice",
            "options": ["3", "4", "5"],
            "correct_answer": 1,
            "points": 1
        }]
    )
    assert 200 <= r_qs.status_code < 300, f"Question creation failed: {r_qs.text}"
    questions = r_qs.json().get("data", [])
    question_id = questions[0].get("id") if questions else None
    assert question_id is not None, "No question ID"
    print(f"[OK] Question added: {question_id}")
    
    print("[14] Starting exam attempt")
    r_attempt = client.post(f"/exams/{exam_id}/attempts", headers=student_headers)
    assert 200 <= r_attempt.status_code < 300, f"Start exam attempt failed: {r_attempt.text}"
    attempt_id = r_attempt.json().get("data", {}).get("id")
    assert attempt_id is not None, "No attempt ID"
    print(f"[OK] Exam attempt started: {attempt_id}")
    
    print("[15] Submitting exam answers")
    answers = [{
        "exam_attempt_id": attempt_id,
        "question_id": question_id,
        "answer_text": 1
    }]
    submit_resp = client.post(
        f"/exams/attempts/{attempt_id}/answers/bulk",
        headers=student_headers,
        json=answers
    )
    assert 200 <= submit_resp.status_code < 300, f"Submit answers failed: {submit_resp.text}"
    print(f"[OK] Exam answers submitted")
    
    print("[16] Completing exam submission")
    submit_exam = client.post(f"/exams/attempts/{attempt_id}/submit", headers=student_headers)
    assert 200 <= submit_exam.status_code < 300, f"Submit exam failed: {submit_exam.text}"
    print(f"[OK] Exam submitted")
    
    print("[17] Retrieving exam attempt")
    attempt_details = client.get(f"/exams/attempts/{attempt_id}", headers=student_headers)
    assert 200 <= attempt_details.status_code < 300, f"Get attempt failed: {attempt_details.text}"
    print(f"[OK] Exam attempt details retrieved")
    
    print("[18] Retrieving student exam statistics")
    stats = client.get("/exams/student/my/stats", headers=student_headers)
    assert 200 <= stats.status_code < 300, f"Get stats failed: {stats.text}"
    print(f"[OK] Student exam statistics retrieved")
    
    print("[SUCCESS] Complete student course progress and results flow verified")
