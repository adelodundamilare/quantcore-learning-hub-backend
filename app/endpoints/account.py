
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.crud.user import user as user_crud
from app.schemas.response import APIResponse
from app.utils import deps
from app.utils.deps import get_current_user
from app.utils.logger import setup_logger
from app.models.user import User
from app.services.email import EmailService

from app.schemas.user import User, UserUpdate, UserInvite, BulkInviteRequest, BulkInviteStatus, AdminUserResponse
from typing import List
from app.services.user import user_service
from fastapi.security import HTTPAuthorizationCredentials
from app.services.auth import auth_service
from app.schemas.response import APIResponse
from app.core.constants import RoleEnum
from app.schemas.trading import AccountBalanceSchema
from app.services.trading import trading_service
from decimal import Decimal
from fastapi import UploadFile, File

logger = setup_logger("account_api", "account.log")

router = APIRouter()

@router.post("/students/{student_id}/add-funds", response_model=APIResponse[AccountBalanceSchema])
async def add_funds_to_student_account(
    student_id: int,
    amount: Decimal,
    db: Session = Depends(deps.get_transactional_db),
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
):
    """Add funds to a student's account."""
    updated_balance = await trading_service.add_funds_to_student_account(
        db,
        student_id=student_id,
        amount=amount,
        current_user_context=context
    )
    return APIResponse(message="Funds added successfully", data=updated_balance)

@router.get("/me", response_model=APIResponse[User])
def read_users_me(current_user: User = Depends(deps.get_current_user)):
    return APIResponse(message="User profile fetched successfully", data=User.model_validate(current_user))

@router.put("/me", response_model=APIResponse[User])
def update_user_me(
    *,
    db: Session = Depends(deps.get_transactional_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user)
):
    updated_user = user_crud.update(db, db_obj=current_user, obj_in=user_in)
    return APIResponse(message="User profile updated successfully", data=User.model_validate(updated_user))

@router.post("/invite", response_model=APIResponse[User])
def invite_user(
    *,
    db: Session = Depends(deps.get_transactional_db),
    invite_in: UserInvite,
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
):
    """Invite a new user (teacher, student, admin, or member) to the current user's school or platform."""
    invited_user = user_service.invite_user(
        db, current_user_context=context, invite_in=invite_in
    )

    return APIResponse(message="User invited successfully", data=User.model_validate(invited_user))

@router.post("/bulk-invite", response_model=APIResponse[dict])
async def bulk_invite_users(
    file: UploadFile = File(...),
    bulk_invite_request: BulkInviteRequest = Depends(),
    db: Session = Depends(deps.get_db),
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
):
    if not context.school:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have a school context to invite users."
        )

    if not (file.filename.lower().endswith(('.csv', '.xlsx', '.xls'))):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a CSV or Excel file."
        )

    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum file size is 10MB."
        )

    try:
        task_id = user_service.start_bulk_invite(
            db=db,
            file_content=file_content,
            filename=file.filename,
            bulk_invite_request=bulk_invite_request,
            school=context.school,
            current_user_context=context
        )

        return APIResponse(
            message="Bulk invite processing started",
            data={"task_id": task_id}
        )

    except Exception as e:
        logger.error(f"Bulk invite error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process bulk invite: {str(e)}"
        )

@router.get("/bulk-invite/{task_id}", response_model=APIResponse[BulkInviteStatus])
def get_bulk_invite_status(
    task_id: str,
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
):
    """Get the status of a bulk invite task."""
    if not context.school:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have a school context to check invite status."
        )

    try:
        status = user_service.get_bulk_invite_status(task_id)
        return APIResponse(
            message="Bulk invite status retrieved successfully",
            data=status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving bulk invite status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bulk invite status"
        )

@router.post("/me/change-password", response_model=APIResponse[None])
async def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(deps.http_bearer)
):
    try:
        user_service.change_password(db, current_user, old_password, new_password)

        EmailService.send_email(
            to_email=current_user.email,
            subject="Password Reset Successfully",
            template_name="reset-password-success.html",
            template_context={}
        )

        # log out current session
        auth_service.logout(db=db, token=credentials.credentials)
        logger.info(f"Password changed for user: {current_user.email}")
        return APIResponse(message="Password updated successfully")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

@router.delete("/me")
async def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        user_crud.delete(db, id=current_user.id)
        logger.info(f"Account deleted: {current_user.email}")
        return {"message": "Account deleted successfully"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

@router.delete("/users/{user_id}", dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
def delete_user_by_admin(
    user_id: int,
    db: Session = Depends(deps.get_transactional_db)
):
    deleted_user = user_service.delete_user_by_admin(db, user_id=user_id)
    return APIResponse(message="User deleted successfully", data=deleted_user)

@router.get("/users/admins", response_model=APIResponse[List[AdminUserResponse]])
def get_admin_users(
    db: Session = Depends(deps.get_db),
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    """Retrieve all users with admin and member roles."""
    user_role_pairs = user_service.get_users_by_roles(
        db, roles=[RoleEnum.MEMBER, RoleEnum.ADMIN],
        current_user_context=context, skip=skip, limit=limit
    )

    data = [
        AdminUserResponse(**user.__dict__, role=role)
        for user, role in user_role_pairs
    ]
    return APIResponse(message="Admin users retrieved successfully", data=data)
