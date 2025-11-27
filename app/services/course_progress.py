from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.course_enrollment import course_enrollment as crud_enrollment
from app.crud.lesson_progress import lesson_progress as crud_lesson_progress
from app.crud.course import course as crud_course
from app.crud.lesson import lesson as crud_lesson
from app.crud.course_reward import course_reward as crud_reward
from app.crud.exam import exam as crud_exam
from app.crud.exam_attempt import exam_attempt as crud_exam_attempt
from app.schemas.user import UserContext
from app.schemas.lesson_progress import LessonProgressCreate
from app.schemas.reward_rating import CourseRewardCreate
from app.models.course_enrollment import EnrollmentStatusEnum
from app.utils.permission import PermissionHelper as permission_helper



class CourseProgressService:

    def _get_or_raise_enrollment(self, db: Session, user_id: int, course_id: int):
        enrollment = crud_enrollment.get_by_user_and_course(db, user_id=user_id, course_id=course_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not enrolled in this course."
            )
        return enrollment

    def _has_passed_course_exam(self, db: Session, enrollment) -> bool:
        """Check if student has passed the final exam for this course."""
        exams = crud_exam.get_exams_by_course(db, course_id=enrollment.course_id)

        if not exams:
            return False

        for exam in exams:
            attempts = crud_exam_attempt.get_by_user_and_exam(
                db, user_id=enrollment.user_id, exam_id=exam.id
            )

            for attempt in attempts:
                if attempt.status == "completed" and attempt.passed == True:
                    return True

        return False

    def _update_course_progress(self, db: Session, enrollment):
        progress = enrollment.calculate_progress()
        enrollment.progress_percentage = progress

        if progress >= 100 and enrollment.status != EnrollmentStatusEnum.COMPLETED:
            enrollment.status = EnrollmentStatusEnum.COMPLETED
            enrollment.completed_at = datetime.now()
            crud_enrollment.update(db, db_obj=enrollment, obj_in={})

        if enrollment.status == EnrollmentStatusEnum.COMPLETED and self._has_passed_course_exam(db, enrollment):
            existing_completion_rewards = crud_reward.get_by_enrollment_and_type(
                db, enrollment_id=enrollment.id, reward_type="completion"
            )
            if not existing_completion_rewards:
                reward_in = CourseRewardCreate(
                    enrollment_id=enrollment.id,
                    reward_type="completion",
                    reward_title=f"Completed {enrollment.course.title}",
                    reward_description=f"Congratulations on completing {enrollment.course.title}!",
                    points=100,
                    awarded_at=datetime.now()
                )
                crud_reward.create(db, obj_in=reward_in)

    async def start_course(self, db: Session, course_id: int, current_user_context: UserContext):
        if not permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only students can start courses."
            )

        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = self._get_or_raise_enrollment(db, current_user_context.user.id, course_id)

        if enrollment.status == EnrollmentStatusEnum.NOT_STARTED:
            enrollment.status = EnrollmentStatusEnum.IN_PROGRESS
            enrollment.started_at = datetime.now()
            crud_enrollment.update(db, db_obj=enrollment, obj_in={})
            db.flush()

        return enrollment

    async def start_lesson(self, db: Session, lesson_id: int, current_user_context: UserContext):
        if not permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only students can start lessons."
            )

        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        course = lesson.curriculum.course if lesson.curriculum else None
        if not course:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson is not associated with a course.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = self._get_or_raise_enrollment(db, current_user_context.user.id, course.id)

        lesson_progress = crud_lesson_progress.get_by_enrollment_and_lesson(
            db, enrollment_id=enrollment.id, lesson_id=lesson_id
        )

        if not lesson_progress:
            progress_in = LessonProgressCreate(
                enrollment_id=enrollment.id,
                lesson_id=lesson_id,
                started_at=datetime.now(),
                last_accessed_at=datetime.now()
            )
            lesson_progress = crud_lesson_progress.create(db, obj_in=progress_in)
        else:
            lesson_progress.last_accessed_at = datetime.now()
            crud_lesson_progress.update(db, db_obj=lesson_progress, obj_in={})

        if enrollment.status == EnrollmentStatusEnum.NOT_STARTED:
            enrollment.status = EnrollmentStatusEnum.IN_PROGRESS
            enrollment.started_at = datetime.now()
            crud_enrollment.update(db, db_obj=enrollment, obj_in={})

        db.flush()
        return lesson_progress

    async def complete_lesson(self, db: Session, lesson_id: int, current_user_context: UserContext):
        if not permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only students can complete lessons."
            )

        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        course = lesson.curriculum.course if lesson.curriculum else None
        if not course:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson is not associated with a course.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = self._get_or_raise_enrollment(db, current_user_context.user.id, course.id)

        lesson_progress = crud_lesson_progress.get_by_enrollment_and_lesson(
            db, enrollment_id=enrollment.id, lesson_id=lesson_id
        )

        if not lesson_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You must start the lesson before completing it."
            )

        if not lesson_progress.is_completed:
            lesson_progress.is_completed = True
            lesson_progress.completed_at = datetime.now()
            crud_lesson_progress.update(db, db_obj=lesson_progress, obj_in={})

            self._update_course_progress(db, enrollment)

        return lesson_progress

    def get_course_progress(self, db: Session, course_id: int, current_user_context: UserContext):
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = self._get_or_raise_enrollment(db, current_user_context.user.id, course_id)
        return enrollment

    def get_completed_lessons(self, db: Session, course_id: int, current_user_context: UserContext) -> List[int]:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = crud_enrollment.get_by_user_and_course(
            db, user_id=current_user_context.user.id, course_id=course_id
        )

        if not enrollment:
            return []

        completed = crud_lesson_progress.get_completed_lesson_ids(db, enrollment_id=enrollment.id)
        return completed

    def get_lesson_progress_details(self, db: Session, course_id: int, current_user_context: UserContext):
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = crud_enrollment.get_by_user_and_course(
            db, user_id=current_user_context.user.id, course_id=course_id
        )

        if not enrollment:
            return []

        progress_records = crud_lesson_progress.get_all_by_enrollment(db, enrollment_id=enrollment.id)
        return progress_records

    def get_user_enrollments(self, db: Session, user_id: int, current_user_context: UserContext):
        if user_id != current_user_context.user.id:
            if permission_helper.is_student(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own enrollments."
                )

        enrollments = crud_enrollment.get_by_user(db, user_id=user_id)
        return enrollments


course_progress_service = CourseProgressService()
