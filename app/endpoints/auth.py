from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.services.school import school_service
from app.models.school import School
from app.schemas.response import APIResponse
from app.schemas.school import SchoolCreate
from app.schemas.user import UserCreate
from app.utils import deps
from app.services.auth import auth_service
from app.schemas.token import ForgotPasswordRequest, LoginResponse, ResendVerificationRequest, ResetPasswordRequest, Token, LoginRequest, VerifyAccountRequest
from app.schemas.response import APIResponse
from app.models.user import User

router = APIRouter()

class SelectContextRequest(BaseModel):
    school_id: int
    role_id: int

class SchoolSignupRequest(BaseModel):
    school: SchoolCreate
    admin: UserCreate

@router.post("/school", response_model=APIResponse[School])
def school_signup(
    *,
    db: Session = Depends(deps.get_db),
    signup_request: SchoolSignupRequest
):
    """Handles the creation of a new school and its administrator."""
    new_school = school_service.create_school_and_admin(
        db=db,
        school_in=signup_request.school,
        admin_in=signup_request.admin
    )
    return APIResponse(message="School and admin created successfully", data=new_school)

@router.post("/login", response_model=APIResponse[LoginResponse])
def login_for_access_token(
    request: LoginRequest,
    db: Session = Depends(deps.get_db)
):
    """Standard OAuth2 login, returns a token and available user contexts."""
    login_data = auth_service.login(db=db, email=request.email, password=request.password)
    return APIResponse(message="Login successful", data=login_data)

@router.post("/select-context", response_model=APIResponse[Token])
def select_context(
    *,
    db: Session = Depends(deps.get_db),
    context_request: SelectContextRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """Exchange a basic token and a context choice for a scoped token."""
    token_data = auth_service.select_context(
        db=db,
        user=current_user,
        school_id=context_request.school_id,
        role_id=context_request.role_id
    )
    return APIResponse(message="Context selected successfully", data=token_data)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: Session = Depends(deps.get_db),
    credentials: HTTPAuthorizationCredentials = Depends(deps.http_bearer)
):
    """Invalidate the current access token by adding it to the denylist."""
    auth_service.logout(db=db, token=credentials.credentials)
    return

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    *,
    db: Session = Depends(deps.get_db),
    request: ForgotPasswordRequest
):
    """Request a password reset link to be sent to the user's email."""
    auth_service.request_password_reset(db=db, email=request.email)
    return {"message": "Password reset link sent if email exists"}
@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    *,
    db: Session = Depends(deps.get_db),
    request: ResetPasswordRequest
):
    """Reset user's password using a valid reset token."""
    auth_service.reset_password(db=db, token=request.token, new_password=request.new_password)
    return

@router.post("/verify-account", response_model=APIResponse[None])
def verify_account(
    *,
    db: Session = Depends(deps.get_db),
    request: VerifyAccountRequest
):
    """Verify user account with a 4-digit code."""
    auth_service.verify_account(db=db, email=request.email, code=request.code)
    return APIResponse(message="Account verified successfully")

@router.post("/resend-verification", response_model=APIResponse[None])
def resend_verification_code(
    *,
    db: Session = Depends(deps.get_db),
    request: ResendVerificationRequest
):
    """Resend account verification code to the user's email."""
    auth_service.resend_verification_code(db=db, email=request.email)
    return APIResponse(message="Verification code resent if account is not verified")