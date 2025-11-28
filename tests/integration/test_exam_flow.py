import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME, EnrollmentStatusEnum
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course
from app.crud.course_enrollment import course_enrollment as enrollment_crud
from app.models.course_enrollment import CourseEnrollment


def test_exam_full_flow(client: TestClient, token_for_role, db_session: Session):
    """
    Test complete exam flow: creation, adding questions, student attempt, submission, results.
    """
    print("\n[TEST] Exam full flow")
    
    headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    assert admin_school is not None, "Admin school not found"
    
    print("[1] Creating course")
    course = crud_course.create(db_session, obj_in={"title": "Exam Flow Course", "school_id": admin_school.id})
    assert course.id is not None, "Course creation failed"
    print(f"[OK] Course created: {course.id}")
    
    print("[2] Creating exam")
    r_exam = client.post("/exams/", headers=headers, json={"title": "Exam Flow", "course_id": course.id})
    assert 200 <= r_exam.status_code < 300, f"Exam creation failed: {r_exam.text}"
    exam_data = r_exam.json().get("data", {})
    exam_id = exam_data.get("id")
    assert exam_id is not None, "No exam ID in response"
    print(f"[OK] Exam created: {exam_id}")
    
    print("[3] Adding questions to exam")
    questions = [
        {
            "exam_id": exam_id,
            "question_text": "What is 2+2?",
            "question_type": "multiple_choice",
            "options": ["3", "4", "5"],
            "correct_answer": 1,
            "points": 1
        },
        {
            "exam_id": exam_id,
            "question_text": "What is 3+3?",
            "question_type": "multiple_choice",
            "options": ["5", "6", "7"],
            "correct_answer": 1,
            "points": 1
        }
    ]
    q_resp = client.post(f"/exams/{exam_id}/questions", headers=headers, json=questions)
    assert 200 <= q_resp.status_code < 300, f"Failed to add questions: {q_resp.text}"
    questions_list = q_resp.json().get("data", [])
    question_ids = [q.get("id") for q in questions_list]
    assert len(question_ids) == 2, "Expected 2 questions"
    print(f"[OK] Questions added to exam: {question_ids}")
    
    print("[4] Getting student token and enrolling in course")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    assert student_me.status_code == 200, f"Failed to get student info: {student_me.text}"
    student_id = student_me.json()["data"]["id"]
    
    enroll_resp = client.post(f"/courses/{course.id}/students/{student_id}", headers=headers)
    assert 200 <= enroll_resp.status_code < 300, f"Enrollment failed: {enroll_resp.text}"
    
    course_enrollment = db_session.query(CourseEnrollment).filter_by(course_id=course.id, user_id=student_id).first()
    if course_enrollment:
        course_enrollment.status = EnrollmentStatusEnum.IN_PROGRESS
        db_session.commit()
    print(f"[OK] Student enrolled in course")
    
    print("[5] Student starting exam attempt")
    attempt_resp = client.post(f"/exams/{exam_id}/attempts", headers=student_headers)
    assert 200 <= attempt_resp.status_code < 300, f"Failed to start exam attempt: {attempt_resp.text}"
    attempt_data = attempt_resp.json().get("data", {})
    attempt_id = attempt_data.get("id")
    assert attempt_id is not None, "No attempt ID in response"
    print(f"[OK] Exam attempt started: {attempt_id}")
    
    print("[6] Student submitting exam answers via bulk endpoint")
    answers = [
        {"exam_attempt_id": attempt_id, "question_id": question_ids[0], "answer_text": 1},
        {"exam_attempt_id": attempt_id, "question_id": question_ids[1], "answer_text": 1}
    ]
    bulk_resp = client.post(
        f"/exams/attempts/{attempt_id}/answers/bulk",
        headers=student_headers,
        json=answers
    )
    assert 200 <= bulk_resp.status_code < 300, f"Failed to submit answers: {bulk_resp.text}"
    print(f"[OK] Exam answers submitted")
    
    print("[7] Student completing exam submission")
    submit_resp = client.post(
        f"/exams/attempts/{attempt_id}/submit",
        headers=student_headers
    )
    assert 200 <= submit_resp.status_code < 300, f"Failed to submit exam: {submit_resp.text}"
    print(f"[OK] Exam submitted")
    
    print("[8] Retrieving exam attempts (for review/grading)")
    attempts_resp = client.get(f"/exams/{exam_id}/attempts", headers=headers)
    assert 200 <= attempts_resp.status_code < 300, f"Failed to get exam attempts: {attempts_resp.text}"
    attempts_list = attempts_resp.json().get("data", [])
    assert len(attempts_list) > 0, "No exam attempts found"
    print(f"[OK] Exam attempts retrieved: {len(attempts_list)} attempt(s)")
    
    print("[SUCCESS] Complete exam flow verified")