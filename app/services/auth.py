from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.token import LoginResponse, SuperAdminCreate, Token, TokenPayload
from app.schemas.token_denylist import TokenDenylistCreate
from app.models.user import User
from app.models.one_time_token import TokenType
from app.crud.token_denylist import token_denylist as crud_token_denylist
from app.crud.one_time_token import one_time_token as crud_one_time_token
from app.crud.role import role as crud_role
from app.core.config import settings
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import string
import random
from app.schemas.user import UserContext
from app.services.email import EmailService
from app.services.notification import notification_service

class AuthService:
    def login(self, db: Session, *, email: str, password: str) -> LoginResponse:
        user = crud_user.get_by_email(db, email=email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not verified or inactive",
            )

        contexts = crud_user.get_user_contexts(db, user_id=user.id)

        pydantic_contexts = []
        for ctx in contexts:
            pydantic_contexts.append(UserContext(school=ctx['school'], role=ctx['role'], user=user))

        if len(pydantic_contexts) == 1:
            context = pydantic_contexts[0]
            token_payload = {
                "user_id": user.id,
                "school_id": context.school.id,
                "role_id": context.role.id
            }
        else:
            token_payload = {"user_id": user.id}

        access_token = create_access_token(data=token_payload, email=user.email)

        return LoginResponse(
            token=Token(access_token=access_token, token_type="bearer"),
            contexts=pydantic_contexts
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

    def request_password_reset(self, db: Session, *, email: str, frontend_base_url: str) -> None:
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

        reset_link = f"{frontend_base_url}/reset-password?token={reset_token_value}"
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
        crud_user.update(db, db_obj=user)

        crud_one_time_token.delete_by_token_value(db, token=token, token_type=TokenType.PASSWORD_RESET)


    def verify_account(self, db: Session, *, email: str, code: str) -> None:
        user = crud_user.get_by_email(db, email=email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        if user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already active.")

        verification_token = crud_one_time_token.get_by_token_value(db, token=code, token_type=TokenType.ACCOUNT_VERIFICATION)
        if not verification_token or verification_token.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code.")

        user.is_active = True
        crud_user.update(db, db_obj=user)
        crud_one_time_token.delete_by_token_value(db, token=code, token_type=TokenType.ACCOUNT_VERIFICATION)


        notification_service.create_notification(
            db,
            user_id=user.id,
            message="Your account has been successfully verified!",
            notification_type="account_verified"
        )

    def resend_verification_code(self, db: Session, *, email: str) -> None:
        user = crud_user.get_by_email(db, email=email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        if user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already verified.")

        crud_one_time_token.delete_by_user_id_and_type(db, user_id=user.id, token_type=TokenType.ACCOUNT_VERIFICATION)

        verification_code = str(random.randint(1000, 9999))
        expires_at = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)

        crud_one_time_token.create(
            db,
            obj_in={
                "user_id": user.id,
                "token": verification_code,
                "token_type": TokenType.ACCOUNT_VERIFICATION,
                "expires_at": expires_at,
            },
        )
        db.commit()

        EmailService.send_email(
            to_email=user.email,
            subject="Resend Account Verification Code",
            template_name="verify_account.html",
            template_context={'user_name': user.full_name, 'verification_code': verification_code}
        )

    def create_super_admin(self, db: Session, *, super_admin_in: SuperAdminCreate) -> User:
        super_admin_role = crud_role.get_by_name(db, name=RoleEnum.SUPER_ADMIN)
        if not super_admin_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{RoleEnum.SUPER_ADMIN}' not found. Please seed the database.",
            )

        existing_user = crud_user.get_by_email(db, email=super_admin_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists.",
            )

        hashed_password = get_password_hash(super_admin_in.password)

        super_admin_data = {
            "full_name": super_admin_in.full_name,
            "email": super_admin_in.email,
            "hashed_password": hashed_password,
            "is_active": True
        }

        new_super_admin = crud_user.create(db, obj_in=super_admin_data, commit=False)

        new_super_admin.role = super_admin_role
        crud_user.update(db, db_obj=new_super_admin)

        notification_service.create_notification(
            db,
            user_id=new_super_admin.id,
            message="Your Super Admin account has been created!",
            notification_type="super_admin_creation"
        )

        return new_super_admin

auth_service = AuthService()