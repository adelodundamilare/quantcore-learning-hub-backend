from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.reward_rating import (
    CourseReward,
    CourseRating, CourseRatingCreate, CourseRatingUpdate, CourseRatingStats
)
from app.services.reward_rating import reward_rating_service
from app.schemas.user import UserContext

router = APIRouter()


@router.post("/enrollments/{enrollment_id}/reward", response_model=APIResponse[CourseReward], status_code=status.HTTP_201_CREATED)
def award_completion_reward(
    *,
    db: Session = Depends(deps.get_transactional_db),
    enrollment_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    reward = reward_rating_service.award_completion_reward(
        db, enrollment_id=enrollment_id, current_user_context=context
    )
    return APIResponse(message="Reward awarded successfully", data=CourseReward.model_validate(reward))


@router.get("/users/{user_id}/rewards", response_model=APIResponse[List[CourseReward]])
def get_user_rewards(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    rewards = reward_rating_service.get_user_rewards(db, user_id=user_id, current_user_context=context)
    return APIResponse(
        message="User rewards retrieved successfully",
        data=[CourseReward.model_validate(r) for r in rewards]
    )


@router.get("/users/{user_id}/points", response_model=APIResponse[dict])
def get_user_total_points(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    points = reward_rating_service.get_user_total_points(db, user_id=user_id, current_user_context=context)
    return APIResponse(message="User points retrieved successfully", data=points)


@router.post("/courses/ratings", response_model=APIResponse[CourseRating], status_code=status.HTTP_201_CREATED)
def create_course_rating(
    *,
    db: Session = Depends(deps.get_transactional_db),
    rating_in: CourseRatingCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    rating = reward_rating_service.create_rating(db, rating_in=rating_in, current_user_context=context)
    return APIResponse(message="Course rated successfully", data=CourseRating.model_validate(rating))


@router.put("/ratings/{rating_id}", response_model=APIResponse[CourseRating])
def update_course_rating(
    *,
    db: Session = Depends(deps.get_transactional_db),
    rating_id: int,
    rating_in: CourseRatingUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    rating = reward_rating_service.update_rating(
        db, rating_id=rating_id, rating_in=rating_in, current_user_context=context
    )
    return APIResponse(message="Rating updated successfully", data=CourseRating.model_validate(rating))


@router.delete("/ratings/{rating_id}", response_model=APIResponse[CourseRating])
def delete_course_rating(
    *,
    db: Session = Depends(deps.get_transactional_db),
    rating_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    rating = reward_rating_service.delete_rating(db, rating_id=rating_id, current_user_context=context)
    return APIResponse(message="Rating deleted successfully", data=CourseRating.model_validate(rating))


@router.get("/courses/{course_id}/ratings", response_model=APIResponse[List[CourseRating]])
def get_course_ratings(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    ratings = reward_rating_service.get_course_ratings(
        db, course_id=course_id, current_user_context=context, skip=skip, limit=limit
    )
    return APIResponse(
        message="Course ratings retrieved successfully",
        data=[CourseRating.model_validate(r) for r in ratings]
    )


@router.get("/courses/{course_id}/rating-stats", response_model=APIResponse[CourseRatingStats])
def get_course_rating_stats(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    stats = reward_rating_service.get_course_rating_stats(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Course rating stats retrieved successfully", data=stats)


@router.get("/courses/{course_id}/my-rating", response_model=APIResponse[CourseRating])
def get_my_course_rating(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    rating = reward_rating_service.get_user_rating_for_course(
        db, course_id=course_id, current_user_context=context
    )
    if not rating:
        return APIResponse(message="You have not rated this course yet", data=None)
    return APIResponse(message="Your rating retrieved successfully", data=CourseRating.model_validate(rating))