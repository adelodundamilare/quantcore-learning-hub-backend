from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import secrets
import string

from app.crud import school as crud_school, user as crud_user, role as crud_role
from app.schemas.school import SchoolCreate
from app.schemas.user import UserCreate
from app.models.school import School
from app.core.security import get_password_hash
from app.core.constants import RoleEnum
from app.services.email import EmailService
from app.services.notification import notification_service

class SchoolService:
    """Service layer for school-related business logic."""

    def create_school_and_admin(
        self, db: Session, *, school_in: SchoolCreate, admin_in: UserCreate
    ) -> School:
        if crud_user.get_by_email(db, email=admin_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists.",
            )

        school_admin_role = crud_role.get_by_name(db, name=RoleEnum.SCHOOL_ADMIN)
        if not school_admin_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{RoleEnum.SCHOOL_ADMIN}' not found. Please seed the database.",
            )

        try:
            new_school = crud_school.create(db, obj_in=school_in, commit=False)

            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
            hashed_password = get_password_hash(temp_password)

            admin_create_data = admin_in.model_dump()
            admin_create_data['password'] = hashed_password
            admin_user_in = UserCreate(**admin_create_data)

            new_admin = crud_user.create(db, obj_in=admin_user_in, commit=False)

            crud_user.add_user_to_school(
                db, user=new_admin, school=new_school, role=school_admin_role
            )

            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during the signup process: {e}",
            )

        db.refresh(new_school)

        EmailService.send_email(
            to_email=new_admin.email,
            subject=f"Welcome to {new_school.name}! Your Admin Account Details",
            template_name="new_account_invite.html",
            template_context={
                'user_name': new_admin.full_name,
                'school_name': new_school.name,
                'role_name': school_admin_role.name,
                'password': temp_password,
                'email': new_admin.email
            }
        )
        notification_service.create_notification(
            db, 
            user_id=new_admin.id, 
            message=f"Welcome! Your school {new_school.name} has been created and you are the administrator.",
            notification_type="school_admin_account",
            link=f"/schools/{new_school.id}" # Example link
        )

        return new_school

school_service = SchoolService()
