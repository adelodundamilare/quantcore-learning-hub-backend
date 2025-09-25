from fastapi import HTTPException, status
from app import schemas
from app.crud.user import user as user_crud
from app.core.security import pwd_context
from .oauth import OAuthService
from app.services.email import EmailService
import string
import secrets

oauth_service = OAuthService()

class UserService:
    def create_user(self, db, user_data):
        if user_crud.get_by_email(db, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        return user_crud.create(db, obj_in=user_data)


    async def get_or_create_google_user(self, db, token):
        user_data = await oauth_service.verify_google_token(token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )

        user = user_crud.get_by_email(db, email=user_data["email"])
        if not user:
            characters = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(characters) for _ in range(8))

            user = user_crud.create(
                db,
                obj_in=schemas.UserCreate(
                    email=user_data["email"],
                    full_name=user_data["name"],
                    auth_provider="google",
                    password=password
                )
            )

            self.update_user(db, user, user_data={
                "verification_code": None,
                "verification_code_expires_at": None,
                "is_verified": True
            })

            EmailService.send_email(
                to_email=user.email,
                subject="Welcome",
                template_name="welcome.html",
                template_context={
                    "name": user.full_name
                }
            )

        return user

    def update_user(self, db, user, user_data):
        # should not change email or password
        return user_crud.update(db, db_obj=user, obj_in=user_data)

    def find_user_by_email(self, db, email):
        user = user_crud.get_by_email(db, email=email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    def change_password(self, db, user, old_password, new_password):
        # Validate new_password
        if not new_password or not new_password.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be empty or contain only whitespace."
            )
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long."
            )
        if new_password.isdigit() or new_password.isalpha():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must contain both letters and numbers."
            )
        if new_password == old_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password."
            )

        if not user_crud.authenticate(db, email=user.email, password=old_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

        self.update_user(
            db,
            user,
            {"hashed_password": pwd_context.hash(new_password)}
        )