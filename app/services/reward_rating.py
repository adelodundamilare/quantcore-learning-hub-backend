from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.course_reward import course_reward as crud_reward
from app.crud.course_rating import course_rating as crud_rating
from app.crud.course_enrollment import course_enrollment as crud_enrollment
from app.crud.course import course as crud_course
from app.schemas.user import UserContext
from app.schemas.reward_rating import ( CourseRewardCreate, CourseRatingCreate, CourseRatingUpdate, CourseRatingStats)
from app.models.course_enrollment import EnrollmentStatusEnum
from app.utils.permission import PermissionHelper as permission_helper
from app.utils.cache import get, set, delete
from app.utils.events import event_bus
import asyncio


class RewardRatingService:

    async def award_completion_reward(self, db: Session, enrollment_id: int, current_user_context: UserContext):
        enrollment = crud_enrollment.get(db, id=enrollment_id)
        if not enrollment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found.")

        if enrollment.status != EnrollmentStatusEnum.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot award reward for incomplete course."
            )

        existing_rewards = crud_reward.get_by_enrollment(db, enrollment_id=enrollment_id)
        if existing_rewards:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reward already awarded for this course."
            )

        reward_in = CourseRewardCreate(
            enrollment_id=enrollment_id,
            reward_type="completion",
            reward_title=f"Completed {enrollment.course.title}",
            reward_description=f"Congratulations on completing {enrollment.course.title}!",
            points=100,
            awarded_at=datetime.now()
        )

        reward = crud_reward.create(db, obj_in=reward_in)
        db.flush()

        delete(f"user_points_{enrollment.user_id}")

        await event_bus.publish("reward_awarded", {
            "student_id": enrollment.user_id,
            "course_id": enrollment.course_id,
            "school_id": enrollment.course.school_id,
            "reward_id": reward.id
        })

        return reward

    def get_user_rewards(self, db: Session, user_id: int, current_user_context: UserContext):
        if user_id != current_user_context.user.id:
            if permission_helper.is_student(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own rewards."
                )

        rewards = crud_reward.get_by_user(db, user_id=user_id)
        return rewards

    def get_user_total_points(self, db: Session, user_id: int, current_user_context: UserContext):
        if user_id != current_user_context.user.id:
            if permission_helper.is_student(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own points."
                )

        cache_key = f"user_points_{user_id}"
        cached = get(cache_key)
        if cached:
            return cached

        total_points = crud_reward.get_total_points_by_user(db, user_id=user_id)
        result = {"user_id": user_id, "total_points": total_points}

        set(cache_key, result, 300)
        return result

    def create_rating(self, db: Session, rating_in: CourseRatingCreate, current_user_context: UserContext):
        if not permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only students can rate courses."
            )

        course = crud_course.get(db, id=rating_in.course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        enrollment = crud_enrollment.get_by_user_and_course(
            db, user_id=current_user_context.user.id, course_id=rating_in.course_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this course to rate it."
            )

        if enrollment.status != EnrollmentStatusEnum.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only rate courses you have completed."
            )

        existing_rating = crud_rating.get_by_user_and_course(
            db, user_id=current_user_context.user.id, course_id=rating_in.course_id
        )

        if existing_rating:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already rated this course. Use update instead."
            )

        rating_data = rating_in.model_dump()
        rating_data['user_id'] = current_user_context.user.id

        rating = crud_rating.create(db, obj_in=rating_data)
        db.flush()
        return rating

    def update_rating(self, db: Session, rating_id: int, rating_in: CourseRatingUpdate,
                     current_user_context: UserContext):
        rating = crud_rating.get(db, id=rating_id)
        if not rating:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found.")

        if rating.user_id != current_user_context.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own ratings."
            )

        updated_rating = crud_rating.update(db, db_obj=rating, obj_in=rating_in)
        return updated_rating

    def delete_rating(self, db: Session, rating_id: int, current_user_context: UserContext):
        rating = crud_rating.get(db, id=rating_id)
        if not rating:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found.")

        if rating.user_id != current_user_context.user.id:
            if not permission_helper.is_super_admin(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own ratings."
                )

        deleted_rating = crud_rating.delete(db, id=rating_id)
        return deleted_rating

    def get_course_ratings(self, db: Session, course_id: int, current_user_context: UserContext,
                          skip: int = 0, limit: int = 100):
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        ratings = crud_rating.get_by_course(db, course_id=course_id, skip=skip, limit=limit)
        return ratings

    def get_course_rating_stats(self, db: Session, course_id: int, current_user_context: UserContext):
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        average_rating = crud_rating.get_average_rating(db, course_id=course_id)
        total_ratings = crud_rating.get_rating_count(db, course_id=course_id)
        rating_distribution = crud_rating.get_rating_distribution(db, course_id=course_id)

        return CourseRatingStats(
            average_rating=average_rating,
            total_ratings=total_ratings,
            rating_distribution=rating_distribution
        )

    def get_user_rating_for_course(self, db: Session, course_id: int, current_user_context: UserContext):
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)

        rating = crud_rating.get_by_user_and_course(
            db, user_id=current_user_context.user.id, course_id=course_id
        )

        return rating


reward_rating_service = RewardRatingService()