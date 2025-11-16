from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.crud.course_enrollment import course_enrollment as crud_enrollment
from app.utils.permission import PermissionHelper as permission_helper

router = APIRouter()


@router.get("/completed", response_model=APIResponse[List[dict]])
def get_completed_enrollments(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int = Query(...),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    permission_helper.require_school_management_permission(context, school_id)

    enrollments = crud_enrollment.get_completed_unrewarded_by_school(db, school_id=school_id)
    return APIResponse(
        message="Completed unrewarded enrollments retrieved",
        data=enrollments
    )


@router.post("/{enrollment_id}/auto-reward", response_model=APIResponse[dict])
async def auto_award_completion_reward(
    *,
    db: Session = Depends(deps.get_transactional_db),
    enrollment_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    from app.services.reward_rating import reward_rating_service
    from app.crud.course_enrollment import course_enrollment as enrollment_crud
    from app.models.course_enrollment import EnrollmentStatusEnum

    enrollment = enrollment_crud.get(db, id=enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    permission_helper.require_school_management_permission(context, enrollment.course.school_id)

    if enrollment.status != EnrollmentStatusEnum.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reward incomplete enrollment")

    try:
        reward = await reward_rating_service.award_completion_reward(db, enrollment_id=enrollment_id, current_user_context=context)
        return APIResponse(message="Reward awarded automatically", data={"points": 100, "reward_id": reward.id})
    except HTTPException as e:
        if "already awarded" in e.detail:
            return APIResponse(message="Reward already awarded", data={"points": 0, "already_awarded": True})
        raise
