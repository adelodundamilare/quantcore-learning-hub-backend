from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import secrets
import string

from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.role import role as crud_role
from app.crud.school import school as crud_school
from app.schemas.school import SchoolCreate
from app.schemas.user import  UserInvite
from app.models.user import User
from app.models.school import School
from app.core.security import get_password_hash
from app.services.email import EmailService
from app.services.notification import notification_service

class UserService:
    def invite_user(
        self, db: Session, *, invited_by: User, school: School, invite_in: UserInvite
    ) -> User:
        """Invites a user to a school as a teacher or student."""
        role_to_assign = crud_role.get_by_name(db, name=invite_in.role_name)
        if not role_to_assign:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{invite_in.role_name}' not found. Please seed the database.",
            )

        existing_user = crud_user.get_by_email(db, email=invite_in.email)

        user_id_to_check = existing_user.id if existing_user else None
        if user_id_to_check:
            existing_association = crud_user.get_association_by_user_school_role(
                db, user_id=user_id_to_check, school_id=school.id, role_id=role_to_assign.id
            )
            if existing_association:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already associated with {school.name} as a {role_to_assign.name}."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already associated with {school.name}."
                )

        if existing_user:
            crud_user.add_user_to_school(
                db, user=existing_user, school=school, role=role_to_assign
            )
            EmailService.send_email(
                to_email=existing_user.email,
                subject=f"You've been added to {school.name}!",
                template_name="added_to_school.html", # Placeholder template
                template_context={'user_name': existing_user.full_name, 'school_name': school.name, 'role_name': role_to_assign.name}
            )
            notification_service.create_notification(
                db,
                user_id=existing_user.id,
                message=f"You have been added to {school.name} as a {role_to_assign.name}.",
                notification_type="school_invitation",
                link=f"/schools/{school.id}" # Example link
            )
            return existing_user
        else:
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
            hashed_password = get_password_hash(temp_password)

            user_in = {
                "full_name": invite_in.full_name,
                "email": invite_in.email,
                "hashed_password": hashed_password,
                "is_active": True # User doesn't need verification
            }

            try:
                new_user = crud_user.create(db, obj_in=user_in, commit=False)
                crud_user.add_user_to_school(
                    db, user=new_user, school=school, role=role_to_assign
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred during the invitation process: {e}",
                )

            EmailService.send_email(
                to_email=new_user.email,
                subject=f"Welcome! Your Invitation Details",
                template_name="new_account_invite.html", # Placeholder template
                template_context={'user_name': new_user.full_name, 'email': new_user.email, 'school_name': school.name, 'role_name': role_to_assign.name, 'password': temp_password}
            )
            notification_service.create_notification(
                db,
                user_id=new_user.id,
                message=f"You have been invited to {school.name} as a {role_to_assign.name}.",
                notification_type="school_invitation",
                link=f"/schools/{school.id}" # Example link
            )
            return new_user

    def admin_invite_user(
        self, db: Session, *, invite_in: UserInvite
    ) -> User:
        """Admin invites a user to a school as a school admin."""
        existing_user = crud_user.get_by_email(db, email=invite_in.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invited user already exists.",
            )

        school_admin_role = crud_role.get_by_name(db, name=RoleEnum.SCHOOL_ADMIN)
        if not school_admin_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{RoleEnum.SCHOOL_ADMIN}' not found. Please seed the database.",
            )

        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
        hashed_password = get_password_hash(temp_password)

        user_in = {
            "full_name": invite_in.full_name,
            "email": invite_in.email,
            "hashed_password": hashed_password,
            "is_active": True # User doesn't need verification
        }

        try:
            new_user = crud_user.create(db, obj_in=user_in)
            new_school = crud_school.create(db=db, obj_in={"name":invite_in.school_name})
            crud_user.add_user_to_school(
                db, user=new_user, school=new_school, role=school_admin_role
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during the invitation process: {e}",
            )

        EmailService.send_email(
            to_email=new_user.email,
            subject=f"Welcome! Your Invitation Details",
            template_name="new_account_invite.html", # Placeholder template
            template_context={'user_name': new_user.full_name, 'email': new_user.email, 'school_name': new_school.name, 'role_name': 'school_admin', 'password': temp_password}
        )
        notification_service.create_notification(
            db,
            user_id=new_user.id,
            message=f"You have been invited to {new_school.name} as a school admin.",
            notification_type="school_invitation",
            link=f"/schools/{new_school.id}" # Example link
        )
        return new_user

user_service = UserService()
