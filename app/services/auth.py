from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.crud import user as crud_user
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.token import LoginResponse, Token, TokenPayload, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.token_denylist import TokenDenylistCreate
from app.models.user import User
from app.models.one_time_token import TokenType
from app.crud.token_denylist import token_denylist as crud_token_denylist
from app.crud.one_time_token import one_time_token as crud_one_time_token
from app.core.config import settings
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import string
from app.services.email import EmailService

class AuthService:
    def login(self, db: Session, *, email: str, password: str) -> LoginResponse:
        user = crud_user.get_by_email(db, email=email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        contexts = crud_user.get_user_contexts(db, user_id=user.id)

        if len(contexts) == 1:
            context = contexts[0]
            token_payload = {
                "user_id": user.id,
                "school_id": context['school'].id,
                "role_id": context['role'].id
            }
        else:
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
        access_token = create_access_token(data=token_payload, email=user.email)
        return Token(access_token=access_token, token_type="bearer")

    def logout(self, db: Session, *, token: str) -> None:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            token_data = TokenPayload(**payload)
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if not token_data.jti or not token_data.exp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token missing JTI or expiration claim")

        crud_token_denylist.create(db, obj_in=TokenDenylistCreate(jti=token_data.jti, exp=datetime.fromtimestamp(token_data.exp)))
        db.commit()

    def request_password_reset(self, db: Session, *, email: str) -> None:
        user = crud_user.get_by_email(db, email=email)
        if not user:
            return

        reset_token_value = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(32))
        expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        crud_one_time_token.create(
            db,
            obj_in={
                "user_id": user.id,
                "token": reset_token_value,
                "token_type": TokenType.PASSWORD_RESET,
                "expires_at": expires_at,
            },
        )
        db.commit()

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token_value}"
        EmailService.send_email(
            to_email=user.email,
            subject="Password Reset Request",
            template_name="reset_password.html",
            template_context={'full_name': user.full_name, 'reset_code': reset_link}
        )

    def reset_password(self, db: Session, *, token: str, new_password: str) -> None:
        reset_token = crud_one_time_token.get_by_token_value(db, token=token, token_type=TokenType.PASSWORD_RESET)
        if not reset_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")

        user = crud_user.get(db, id=reset_token.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        user.hashed_password = get_password_hash(new_password)
        crud_user.update(db, db_obj=user, obj_in=user)

        crud_one_time_token.delete_by_token_value(db, token=token, token_type=TokenType.PASSWORD_RESET)
        db.commit()

auth_service = AuthService()