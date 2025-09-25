from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.crud import user as crud_user
from app.core.security import verify_password, create_access_token
from app.schemas.token import LoginResponse, Token
from app.models.user import User

class AuthService:
    def login(self, db: Session, *, form_data: OAuth2PasswordRequestForm) -> LoginResponse:
        user = crud_user.get_by_email(db, email=form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        
        contexts = crud_user.get_user_contexts(db, user_id=user.id)
        
        if len(contexts) == 1:
            # Auto-select context for single-school users
            context = contexts[0]
            token_payload = {
                "user_id": user.id,
                "school_id": context['school'].id,
                "role_id": context['role'].id
            }
        else:
            # Requires context selection for multi-school users or users with no school
            token_payload = {"user_id": user.id}

        access_token = create_access_token(data=token_payload)
        
        return LoginResponse(
            token=Token(access_token=access_token, token_type="bearer"),
            contexts=contexts
        )

    def select_context(
        self, db: Session, *, user: User, school_id: int, role_id: int
    ) -> Token:
        contexts = crud_user.get_user_contexts(db, user_id=user.id)
        
        # Verify the user actually belongs to the requested context
        is_valid_context = any(
            c['school'].id == school_id and c['role'].id == role_id for c in contexts
        )

        if not is_valid_context:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to the specified context."
            )

        token_payload = {
            "user_id": user.id,
            "school_id": school_id,
            "role_id": role_id
        }
        access_token = create_access_token(data=token_payload)
        return Token(access_token=access_token, token_type="bearer")

auth_service = AuthService()