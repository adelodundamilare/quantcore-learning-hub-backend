from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.utils import deps
from app.services.auth import auth_service
from app.schemas.token import ForgotPasswordRequest, LoginResponse, ResetPasswordRequest, Token
from app.models.user import User

router = APIRouter()

class SelectContextRequest(BaseModel):
    school_id: int
    role_id: int

@router.post("/token", response_model=LoginResponse)
def login_for_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Standard OAuth2 login, returns a token and available user contexts."""
    return auth_service.login(db=db, form_data=form_data)

@router.post("/select-context", response_model=Token)
def select_context(
    *,
    db: Session = Depends(deps.get_db),
    context_request: SelectContextRequest,
    # This uses a basic token that only contains user_id
    current_user: User = Depends(deps.get_current_user)
):
    """Exchange a basic token and a context choice for a scoped token."""
    return auth_service.select_context(
        db=db,
        user=current_user,
        school_id=context_request.school_id,
        role_id=context_request.role_id
    )

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