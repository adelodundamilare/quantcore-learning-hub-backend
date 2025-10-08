from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import secrets
import string

from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.role import role as crud_role
from app.crud.school import school as crud_school
from app.schemas.user import  TeacherUpdate, UserContext, UserInvite
from app.models.user import User
from app.models.school import School
from app.core.security import get_password_hash, verify_password
from app.services.email import EmailService
from app.utils.permission import PermissionHelper as permission_helper
from app.services.notification import notification_service
from app.services.course import course_service

class UserService:

    def change_password(self, db: Session, user: User, old_password: str, new_password: str):
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password.")

        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.add(user)
        db.commit()
        db.refresh(user)

        # Optionally, send a notification email
        EmailService.send_email(
            to_email=user.email,
            subject="Your Password Has Been Changed",
            template_name="reset-password-success.html",  # You might need to create this template
            template_context={'user_name': user.full_name}
        )

        return user

    def get_students_for_school(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[User]:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        return crud_user.get_users_by_school_and_role(db, school_id=school_id, role_id=student_role.id, skip=skip, limit=limit)

    def get_teachers_for_school(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[User]:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        teacher_role = crud_role.get_by_name(db, name=RoleEnum.TEACHER)
        if not teacher_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Teacher role not found.")

        return crud_user.get_users_by_school_and_role(db, school_id=school_id, role_id=teacher_role.id, skip=skip, limit=limit)

    def get_teams_for_school(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[User]:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        return crud_user.get_non_student_users_by_school(db, school_id=school_id, skip=skip, limit=limit)

    def invite_user(
        self, db: Session, *, school: School, invite_in: UserInvite, current_user_context: UserContext
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
                db, user=existing_user, school=school, role=role_to_assign, level=invite_in.level
            )

            if invite_in.course_ids and role_to_assign.name == RoleEnum.STUDENT:
                for course_id in invite_in.course_ids:
                    try:
                        course_service.enroll_student(db, course_id=course_id, user_id=existing_user.id, current_user_context=current_user_context)
                    except HTTPException as e:
                        print(f"Warning: Could not enroll existing user {existing_user.id} in course {course_id}: {e.detail}")

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
                    db, user=new_user, school=school, role=role_to_assign, level=invite_in.level
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred during the invitation process: {e}",
                )

            if invite_in.course_ids and role_to_assign.name == RoleEnum.STUDENT:
                for course_id in invite_in.course_ids:
                    try:
                        course_service.enroll_student(db, course_id=course_id, user_id=new_user.id, current_user_context=current_user_context)
                    except HTTPException as e:
                        print(f"Warning: Could not enroll new user {new_user.id} in course {course_id}: {e.detail}")

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

    def update_teacher_details(self, db: Session, school_id: int, teacher_id: int, update_data: TeacherUpdate, current_user_context: UserContext):
        permission_helper.require_school_management_permission(current_user_context, school_id)

        teacher_role = crud_role.get_by_name(db, name=RoleEnum.TEACHER)
        if not teacher_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Teacher role not found.")

        association = crud_user.get_association_by_user_school_role(
            db, user_id=teacher_id, school_id=school_id, role_id=teacher_role.id
        )
        if not association:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found in this school.")

        crud_user.update_association(db, user_id=teacher_id, school_id=school_id, level=update_data.level)

        updated_teacher = crud_user.get(db, id=teacher_id)
        return updated_teacher

user_service = UserService()
