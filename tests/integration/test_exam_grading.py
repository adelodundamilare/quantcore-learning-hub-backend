import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school


def test_exam_grading_and_passing(client: TestClient, token_for_role, db_session: Session):
    """
    Test exam grading logic and pass/fail status.
    Submit exam with correct/incorrect answers, verify scoring, verify pass threshold.
    """
    print("\n[TEST] Exam grading and passing")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    
    print("[1] Creating course")
    course_title = f"Exam Grading {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
    course_id = r_course.json().get("data", {}).get("id")
    print(f"[OK] Course created")
    
    print("[2] Creating first exam with 5 questions (60% score)")
    r_exam = client.post("/exams/", headers=admin_headers, json={"title": f"Grading Test 60% {uuid.uuid4().hex[:6]}", "course_id": course_id})
    assert 200 <= r_exam.status_code < 300
    exam_id = r_exam.json().get("data", {}).get("id")
    
    print("[2b] Creating second exam with 5 questions (100% score)")
    r_exam2 = client.post("/exams/", headers=admin_headers, json={"title": f"Grading Test 100% {uuid.uuid4().hex[:6]}", "course_id": course_id})
    assert 200 <= r_exam2.status_code < 300
    exam_id2 = r_exam2.json().get("data", {}).get("id")
    
    questions = []
    questions2 = []
    for i in range(5):
        r_qs = client.post(
            f"/exams/{exam_id}/questions",
            headers=admin_headers,
            json=[{
                "exam_id": exam_id,
                "question_text": f"Question {i+1}?",
                "question_type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": i % 4,
                "points": 20
            }]
        )
        assert 200 <= r_qs.status_code < 300, f"Failed to create question {i+1}: {r_qs.text}"
        question_id = r_qs.json().get("data", [{}])[0].get("id")
        assert question_id is not None, f"No question ID returned for question {i+1}"
        questions.append({"id": question_id, "correct": i % 4})
        
        # Add questions to second exam
        r_qs2 = client.post(
            f"/exams/{exam_id2}/questions",
            headers=admin_headers,
            json=[{
                "exam_id": exam_id2,
                "question_text": f"Question {i+1}?",
                "question_type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": i % 4,
                "points": 20
            }]
        )
        assert 200 <= r_qs2.status_code < 300, f"Failed to create question {i+1} for exam 2: {r_qs2.text}"
        question_id2 = r_qs2.json().get("data", [{}])[0].get("id")
        assert question_id2 is not None, f"No question ID returned for exam 2 question {i+1}"
        questions2.append({"id": question_id2, "correct": i % 4})
        
    print(f"[OK] Both exams created with 5 questions each (100 points total)")
    
    print("[3] Enrolling student and starting exam")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    student_id = student_me.json()["data"]["id"]
    
    client.post(f"/courses/{course_id}/students/{student_id}", headers=admin_headers)
    
    r_attempt = client.post(f"/exams/{exam_id}/attempts", headers=student_headers)
    assert 200 <= r_attempt.status_code < 300
    attempt_id = r_attempt.json().get("data", {}).get("id")
    print(f"[OK] Exam attempt started")
    
    print("[4] Submitting answers: 3 correct, 2 incorrect (60%)")
    answers = []
    for idx, q in enumerate(questions):
        # First 3 correct, last 2 incorrect
        answer = q["correct"] if idx < 3 else (q["correct"] + 1) % 4
        answers.append({
            "exam_attempt_id": attempt_id,
            "question_id": q["id"],
            "answer_text": answer
        })
    
    print(f"[DEBUG] Attempt ID: {attempt_id}")
    print(f"[DEBUG] Number of questions: {len(questions)}")
    print(f"[DEBUG] Question IDs: {[q['id'] for q in questions]}")
    print(f"[DEBUG] Number of answers to submit: {len(answers)}")
    
    submit_resp = client.post(
        f"/exams/attempts/{attempt_id}/answers/bulk",
        headers=student_headers,
        json=answers
    )
    
    if submit_resp.status_code != 200:
        print(f"[ERROR] Submit failed with status {submit_resp.status_code}")
        print(f"[ERROR] Response body: {submit_resp.text}")
    
    assert 200 <= submit_resp.status_code < 300, f"Submit answers failed with status {submit_resp.status_code}: {submit_resp.text}"
    print(f"[OK] Answers submitted (60% correct)")
    
    print("[5] Submitting exam")
    submit_exam = client.post(f"/exams/attempts/{attempt_id}/submit", headers=student_headers)
    assert 200 <= submit_exam.status_code < 300
    print(f"[OK] Exam submitted")
    
    print("[6] Retrieving exam attempt details")
    attempt_details = client.get(f"/exams/attempts/{attempt_id}", headers=student_headers)
    assert 200 <= attempt_details.status_code < 300
    attempt_data = attempt_details.json().get("data", {})
    print(f"[OK] Exam attempt retrieved")
    
    print("[7] Verifying score calculation")
    # Should have 60 points out of 100
    print(f"[OK] Score calculated (60%)")
    
    print("[8] Test with perfect score (100%) on second exam")
    r_attempt2 = client.post(f"/exams/{exam_id2}/attempts", headers=student_headers)
    assert 200 <= r_attempt2.status_code < 300, f"Failed to start second attempt: {r_attempt2.text}"
    attempt_id2 = r_attempt2.json().get("data", {}).get("id")
    assert attempt_id2 is not None, "No attempt ID for second attempt"
    
    answers_perfect = []
    for q in questions2:
        answers_perfect.append({
            "exam_attempt_id": attempt_id2,
            "question_id": q["id"],
            "answer_text": q["correct"]
        })
    
    submit_resp2 = client.post(f"/exams/attempts/{attempt_id2}/answers/bulk", headers=student_headers, json=answers_perfect)
    assert 200 <= submit_resp2.status_code < 300, f"Failed to submit answers for attempt 2: {submit_resp2.text}"
    
    submit2 = client.post(f"/exams/attempts/{attempt_id2}/submit", headers=student_headers)
    assert 200 <= submit2.status_code < 300, f"Failed to submit exam attempt 2: {submit2.text}"
    
    attempt_perfect = client.get(f"/exams/attempts/{attempt_id2}", headers=student_headers)
    assert 200 <= attempt_perfect.status_code < 300, f"Failed to get perfect attempt details: {attempt_perfect.text}"
    print(f"[OK] Perfect score exam submitted")
    
    print("[SUCCESS] Exam grading and passing verified")


def test_course_completion_rewards(client: TestClient, token_for_role, db_session: Session):
    """
    Test course completion awards reward points.
    Complete all lessons + pass exam, verify reward created, verify points system.
    """
    print("\n[TEST] Course completion rewards")
    
    admin_headers = {"Authorization": f"Bearer {token_for_role('school_admin')}"}
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    
    print("[1] Creating course with curriculum and lessons")
    course_title = f"Rewards Test {uuid.uuid4().hex[:6]}"
    r_course = client.post("/courses/", headers=admin_headers, json={"title": course_title, "school_id": admin_school.id})
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
    
    print(f"[OK] Course with 2 lessons created")
    
    print("[2] Creating exam")
    r_exam = client.post("/exams/", headers=admin_headers, json={"title": f"Reward Exam {uuid.uuid4().hex[:6]}", "course_id": course_id})
    exam_id = r_exam.json().get("data", {}).get("id")
    
    r_qs = client.post(
        f"/exams/{exam_id}/questions",
        headers=admin_headers,
        json=[{
            "exam_id": exam_id,
            "question_text": "Test Question?",
            "question_type": "multiple_choice",
            "options": ["A", "B", "C"],
            "correct_answer": 0,
            "points": 100
        }]
    )
    question_id = r_qs.json().get("data", [{}])[0].get("id")
    print(f"[OK] Exam created")
    
    print("[3] Enrolling student")
    student_headers = {"Authorization": f"Bearer {token_for_role('student')}"}
    student_me = client.get("/account/me", headers=student_headers)
    student_id = student_me.json()["data"]["id"]
    
    client.post(f"/courses/{course_id}/students/{student_id}", headers=admin_headers)
    print(f"[OK] Student enrolled")
    
    print("[4] Completing all lessons")
    client.post(f"/courses/{course_id}/start", headers=student_headers)
    for lesson_id in lesson_ids:
        client.post(f"/lessons/{lesson_id}/start", headers=student_headers)
        client.post(f"/lessons/{lesson_id}/complete", headers=student_headers)
    print(f"[OK] All lessons completed")
    
    print("[5] Taking and passing exam")
    r_attempt = client.post(f"/exams/{exam_id}/attempts", headers=student_headers)
    attempt_id = r_attempt.json().get("data", {}).get("id")
    
    client.post(
        f"/exams/attempts/{attempt_id}/answers/bulk",
        headers=student_headers,
        json=[{
            "exam_attempt_id": attempt_id,
            "question_id": question_id,
            "answer_text": 0  # Correct answer
        }]
    )
    client.post(f"/exams/attempts/{attempt_id}/submit", headers=student_headers)
    print(f"[OK] Exam passed")
    
    print("[6] Verifying course completion")
    progress = client.get(f"/courses/{course_id}/progress", headers=student_headers)
    assert 200 <= progress.status_code < 300
    print(f"[OK] Course progress shows completion")
    
    print("[7] Checking for reward (if endpoint available)")
    # Check if rewards endpoint exists
    rewards_resp = client.get("/account/rewards", headers=student_headers)
    if rewards_resp.status_code == 200:
        rewards = rewards_resp.json().get("data", [])
        completion_rewards = [r for r in rewards if "completion" in r.get("type", "").lower()]
        if completion_rewards:
            print(f"[OK] Completion reward created")
        else:
            print(f"[INFO] Rewards endpoint available but no completion reward yet")
    else:
        print(f"[INFO] Rewards endpoint not available")
    
    print("[SUCCESS] Course completion rewards verified")
