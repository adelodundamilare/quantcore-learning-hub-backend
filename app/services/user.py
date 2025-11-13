from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import secrets
import string
import uuid
import pandas as pd
from datetime import datetime
import io

from app.core.constants import ADMIN_SCHOOL_NAME
from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.role import role as crud_role
from app.crud.school import school as crud_school
from app.crud.course_enrollment import course_enrollment as crud_course_enrollment
from app.crud.curriculum import curriculum as crud_curriculum
from app.crud.course import course as crud_course
from app.schemas.user import (
    TeacherProfile, TeacherUpdate, UserContext, UserInvite, User as UserSchema,
    StudentProfile, BulkInviteRequest, BulkInviteResult, BulkInviteStatus
)
from app.models.user import User
from app.models.school import School
from app.core.security import get_password_hash, verify_password
from app.services.email import EmailService
from app.utils.permission import PermissionHelper as permission_helper
from app.services.notification import notification_service
from app.services.course import course_service
from app.services.trading import trading_service
from app.utils.logger import setup_logger
import re

logger = setup_logger("user_service", "user_service.log")

class UserService:

    def change_password(self, db: Session, user: User, old_password: str, new_password: str):
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password.")

        hashed_password = get_password_hash(new_password)
        updated_user = crud_user.update_user_password(db, user=user, hashed_password=hashed_password)

        EmailService.send_email(
            to_email=user.email,
            subject="Your Password Has Been Changed",
            template_name="reset-password-success.html",
            template_context={'user_name': user.full_name}
        )

        return updated_user

    def get_students_for_school(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[UserSchema]:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        return crud_user.get_users_by_school_and_role(db, school_id=school_id, role_id=student_role.id, skip=skip, limit=limit)

    def get_teachers_for_school(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[UserSchema]:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        teacher_role = crud_role.get_by_name(db, name=RoleEnum.TEACHER)
        if not teacher_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Teacher role not found.")

        return crud_user.get_users_by_school_and_role(db, school_id=school_id, role_id=teacher_role.id, skip=skip, limit=limit)

    def get_teams_for_school(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[UserSchema]:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        return crud_user.get_non_student_users_by_school(db, school_id=school_id, skip=skip, limit=limit)

    def invite_user(
        self, db: Session, *, invite_in: UserInvite, current_user_context: UserContext
    ) -> UserSchema:
        """Invites a user to a school as a teacher/student or as a platform admin/member."""
        inviting_role = current_user_context.role.name
        invited_role = invite_in.role_name
        is_platform_invite = invited_role in [RoleEnum.ADMIN, RoleEnum.MEMBER]

        if inviting_role == RoleEnum.SUPER_ADMIN:
            pass
        elif is_platform_invite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admins can invite platform-level users."
            )
        else:
            if not current_user_context.school:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You must have a school context to invite school users."
                )

            if inviting_role == RoleEnum.SCHOOL_ADMIN:
                if invited_role not in [RoleEnum.TEACHER, RoleEnum.STUDENT]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="School Admins can only invite Teachers or Students."
                    )
            elif inviting_role == RoleEnum.TEACHER:
                if invited_role != RoleEnum.STUDENT:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Teachers can only invite Students."
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your role does not have permission to invite users."
                )

        role_to_assign = crud_role.get_by_name(db, name=invite_in.role_name)
        if not role_to_assign:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{invite_in.role_name}' not found. Please seed the database.",
            )

        if is_platform_invite:
            admin_school = crud_school.get_by_name(db, name=ADMIN_SCHOOL_NAME)
            if not admin_school:
                admin_school = crud_school.create(db, obj_in={"name": ADMIN_SCHOOL_NAME}, commit=True)
            target_school = admin_school
        else:
            target_school = current_user_context.school

        existing_user = crud_user.get_by_email(db, email=invite_in.email)

        user_id_to_check = existing_user.id if existing_user else None
        if user_id_to_check:
            existing_association = crud_user.get_association_by_user_school_role(
                db, user_id=user_id_to_check, school_id=target_school.id, role_id=role_to_assign.id
            )
            if existing_association:
                school_name = "platform" if is_platform_invite else target_school.name
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already associated with {school_name} as a {role_to_assign.name}."
                )
            else:
                school_name = "platform" if is_platform_invite else target_school.name
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User is already associated with {school_name}."
                )

        if existing_user:
            crud_user.add_user_to_school(
                db, user=existing_user, school=target_school, role=role_to_assign, level=invite_in.level
            )

            if invite_in.course_ids and role_to_assign.name == RoleEnum.STUDENT and not is_platform_invite:
                for course_id in invite_in.course_ids:
                    try:
                        course_service.enroll_student(db, course_id=course_id, user_id=existing_user.id, current_user_context=current_user_context)
                    except HTTPException as e:
                        print(f"Warning: Could not enroll existing user {existing_user.id} in course {course_id}: {e.detail}")

            school_name = "platform" if is_platform_invite else target_school.name
            role_display = f"platform {role_to_assign.name}" if is_platform_invite else role_to_assign.name

            EmailService.send_email(
                to_email=existing_user.email,
                subject=f"You've been added to {school_name}!",
                template_name="added_to_school.html",
                template_context={'user_name': existing_user.full_name, 'school_name': school_name, 'role_name': role_display}
            )
            notification_service.create_notification(
                db,
                user_id=existing_user.id,
                message=f"You have been added to {school_name} as a {role_display}.",
                notification_type="school_invitation" if not is_platform_invite else "platform_invitation",
                link=f"/schools/{target_school.id}" if not is_platform_invite else "/admin"
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
                    db, user=new_user, school=target_school, role=role_to_assign, level=invite_in.level
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An error occurred during the invitation process: {e}",
                )

            if invite_in.course_ids and role_to_assign.name == RoleEnum.STUDENT and not is_platform_invite:
                for course_id in invite_in.course_ids:
                    try:
                        course_service.enroll_student(db, course_id=course_id, user_id=new_user.id, current_user_context=current_user_context)
                    except HTTPException as e:
                        print(f"Warning: Could not enroll new user {new_user.id} in course {course_id}: {e.detail}")

            school_name = "platform" if is_platform_invite else target_school.name
            role_display = f"platform {role_to_assign.name}" if is_platform_invite else role_to_assign.name

            EmailService.send_email(
                to_email=new_user.email,
                subject=f"Welcome! Your Invitation Details",
                template_name="new_account_invite.html",
                template_context={'user_name': new_user.full_name, 'email': new_user.email, 'school_name': school_name, 'role_name': role_display, 'password': temp_password}
            )
            notification_service.create_notification(
                db,
                user_id=new_user.id,
                message=f"You have been invited to {school_name} as a {role_display}.",
                notification_type="school_invitation" if not is_platform_invite else "platform_invitation",
                link=f"/schools/{target_school.id}" if not is_platform_invite else "/admin"
            )
            return new_user

    def admin_invite_user(
        self, db: Session, *, invite_in: UserInvite
    ) -> UserSchema:
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
            link=f"/schools/{new_school.id}"
        )
        return new_user

    def update_teacher_details(self, db: Session, school_id: int, teacher_id: int, update_data: TeacherUpdate, current_user_context: UserContext) -> UserSchema:
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

    def remove_user_from_school(self, db: Session, school_id: int, user_id: int, current_user_context: UserContext) -> dict:
        """Remove a user from a school (soft delete)."""
        permission_helper.require_school_management_permission(current_user_context, school_id)

        if current_user_context.user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove yourself from the school."
            )

        association_result = crud_user.get_association_by_user_and_school(db, user_id=user_id, school_id=school_id)
        if not association_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school."
            )

        role = association_result[0]
        association = association_result[1]

        school_admin_role = crud_role.get_by_name(db, name=RoleEnum.SCHOOL_ADMIN)
        if role.id == school_admin_role.id:
            admin_count = crud_user.get_school_admin_count(db, school_id=school_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last school administrator."
                )

        user = crud_user.get(db, id=user_id)

        crud_user.soft_delete_user_association(db, user_id=user_id, school_id=school_id)

        logger.info(f"User {user_id} ({user.email}) removed from school {school_id} by admin {current_user_context.user.id} ({current_user_context.user.email})")

        courses = crud_course.get_courses_by_school(db, school_id=school_id)
        for course in courses:
            try:
                course_service.unenroll_student(db, course_id=course.id, user_id=user_id, current_user_context=current_user_context)
            except HTTPException:
                pass

        notification_service.create_notification(
            db,
            user_id=user_id,
            message=f"You have been removed from {current_user_context.school.name}.",
            notification_type="school_removal",
            link=f"/schools"
        )

        return {"message": "User removed from school successfully"}

    def update_user_role(self, db: Session, school_id: int, user_id: int, update_data, current_user_context: UserContext) -> UserSchema:
        """Update a user's role within a school."""
        permission_helper.require_school_management_permission(current_user_context, school_id)

        association_result = crud_user.get_association_by_user_and_school(db, user_id=user_id, school_id=school_id)
        if not association_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school."
            )

        role = association_result[0]
        association = association_result[1]
        old_role = role.name

        new_role = crud_role.get_by_name(db, name=update_data.role_name)
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role '{update_data.role_name}' not found. Please seed the database."
            )

        existing_association = crud_user.get_association_by_user_school_role(
            db, user_id=user_id, school_id=school_id, role_id=new_role.id
        )
        if existing_association:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User already has the role '{update_data.role_name}' in this school."
            )

        crud_user.update_association(
            db, user_id=user_id, school_id=school_id,
            role_id=new_role.id, level=update_data.level
        )

        user = crud_user.get(db, id=user_id)
        logger.info(f"User {user_id} ({user.email}) role changed from {old_role} to {new_role.name} in school {school_id} by admin {current_user_context.user.id} ({current_user_context.user.email})")

        notification_service.create_notification(
            db,
            user_id=user_id,
            message=f"Your role has been updated to {new_role.name} in {current_user_context.school.name}.",
            notification_type="role_update",
            link=f"/schools/{school_id}"
        )

        updated_user = crud_user.get(db, id=user_id)
        return updated_user

    def update_user_status(self, db: Session, school_id: int, user_id: int, update_data, current_user_context: UserContext) -> UserSchema:
        """Update a user's active status within a school."""
        permission_helper.require_school_management_permission(current_user_context, school_id)

        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        association_result = crud_user.get_association_by_user_and_school(db, user_id=user_id, school_id=school_id)
        if not association_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school."
            )

        role = association_result[0]
        association = association_result[1]

        if not update_data.is_active and role.name == RoleEnum.SCHOOL_ADMIN:
            admin_count = crud_user.get_school_admin_count(db, school_id=school_id)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last school administrator."
                )

        old_status = user.is_active

        updated_user = crud_user.update_user_active_status(db, user=user, is_active=update_data.is_active)

        status_text = "activated" if update_data.is_active else "deactivated"
        logger.info(f"User {user_id} ({user.email}) {status_text} in school {school_id} by admin {current_user_context.user.id} ({current_user_context.user.email})")

        notification_service.create_notification(
            db,
            user_id=user_id,
            message=f"Your account has been {status_text} in {current_user_context.school.name}.",
            notification_type="status_update",
            link=f"/schools/{school_id}"
        )

        return user

    def update_user_details_admin(self, db: Session, school_id: int, user_id: int, update_data: dict, current_user_context: UserContext) -> UserSchema:
        """Update user details administratively within a school context."""
        permission_helper.require_school_management_permission(current_user_context, school_id)

        association_result = crud_user.get_association_by_user_and_school(db, user_id=user_id, school_id=school_id)
        if not association_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this school."
            )

        role = association_result[0]
        association = association_result[1]

        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        if update_data.get('email') and update_data['email'] != user.email:
            existing_user = crud_user.get_by_email(db, email=update_data['email'])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already in use by another user."
                )

        # Get old values for logging
        old_email = user.email
        old_full_name = user.full_name

        updated_user = crud_user.update(db, db_obj=user, obj_in=update_data)

        # Audit logging
        changes = []
        if update_data.get('email') and update_data['email'] != old_email:
            changes.append(f"email: {old_email} -> {update_data['email']}")
        if update_data.get('full_name') and update_data['full_name'] != old_full_name:
            changes.append(f"name: {old_full_name} -> {update_data['full_name']}")

        if changes:
            logger.info(f"User {user_id} details updated in school {school_id} by admin {current_user_context.user.id} ({current_user_context.user.email}): {', '.join(changes)}")

        notification_service.create_notification(
            db,
            user_id=user_id,
            message=f"Your profile details have been updated by an administrator.",
            notification_type="profile_update",
            link=f"/profile"
        )

        return updated_user

    def get_users_by_roles(self, db: Session, roles: List[RoleEnum], current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[tuple[UserSchema, str]]:
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this resource.")

        role_names = [role.value for role in roles]
        user_role_pairs = crud_user.get_users_by_role_names(db, role_names=role_names, skip=skip, limit=limit)
        return [(UserSchema.model_validate(user), role.name) for user, role in user_role_pairs]

    def get_user_profile_for_school(self, db: Session, school_id: int, user_id: int, current_user_context: UserContext) -> UserSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if not any(school.id == school_id for school in user.schools):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in this school.")

        return user

    async def get_student_profile_for_school(self, db: Session, school_id: int, student_id: int, current_user_context: UserContext) -> StudentProfile:
        user = self.get_user_profile_for_school(db, school_id, student_id, current_user_context)

        if not permission_helper.is_student(current_user_context):
            student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
            if not student_role:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

            association = crud_user.get_association_by_user_school_role(
                db, user_id=student_id, school_id=school_id, role_id=student_role.id
            )
            if not association:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not a student in this school.")

        assigned_lessons_count = 0
        enrollments = crud_course_enrollment.get_by_user(db, user_id=student_id)
        for enrollment in enrollments:
            if enrollment.course:
                curriculums = crud_curriculum.get_by_course(db, course_id=enrollment.course.id)
                for curriculum in curriculums:
                    assigned_lessons_count += len(curriculum.lessons)

        trading_summary = await trading_service.get_trading_account_summary(db, user_id=student_id)

        association_result = crud_user.get_association_by_user_and_school(db, user_id=student_id, school_id=school_id)
        role = association_result[0] if association_result else None
        association = association_result[1] if association_result else None
        student_level = association.level if association else None

        pydantic_user = UserSchema.model_validate(user)
        user_data = pydantic_user.model_dump()
        user_data["assigned_lessons_count"] = assigned_lessons_count
        user_data["trading_fund_balance"] = trading_summary
        user_data["level"] = student_level

        return StudentProfile.model_validate(user_data)

    async def get_teacher_profile_for_school(self, db: Session, school_id: int, teacher_id: int, current_user_context: UserContext) -> TeacherProfile:
        user = self.get_user_profile_for_school(db, school_id, teacher_id, current_user_context)

        if not permission_helper.is_teacher(current_user_context):
            teacher_role = crud_role.get_by_name(db, name=RoleEnum.TEACHER)
            if not teacher_role:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Teacher role not found.")

            association = crud_user.get_association_by_user_school_role(
                db, user_id=teacher_id, school_id=school_id, role_id=teacher_role.id
            )
            if not association:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not a teacher in this school.")

        teacher_courses = crud_course.get_teacher_courses(db, user_id=teacher_id)
        total_students_taught = sum(
            crud_course_enrollment.get_student_count_for_course(db, course_id=course.id)
            for course in teacher_courses
        )

        association_result = crud_user.get_association_by_user_and_school(db, user_id=teacher_id, school_id=school_id)
        role = association_result[0] if association_result else None
        association = association_result[1] if association_result else None
        teacher_level = association.level if association else None

        user_data = UserSchema.model_validate(user).model_dump()
        user_data["num_students_taught"] = total_students_taught
        user_data["level"] = teacher_level

        return TeacherProfile.model_validate(user_data)

    _bulk_invite_tasks: Dict[str, BulkInviteStatus] = {}

    def parse_invite_file(self, file_content: bytes, filename: str) -> pd.DataFrame:
        try:
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content))
            elif filename.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise ValueError("Unsupported file format. Please upload CSV or Excel files.")

            required_columns = ['email', 'full_name', 'role']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

            df = df.dropna(subset=required_columns)
            df['email'] = df['email'].astype(str).str.strip().str.lower()
            df['full_name'] = df['full_name'].astype(str).str.strip()
            df['role'] = df['role'].astype(str).str.strip().str.lower()

            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            valid_emails = df['email'].str.match(email_pattern)
            if not valid_emails.all():
                invalid_emails = df[~valid_emails]['email'].tolist()
                raise ValueError(f"Invalid email format(s): {', '.join(invalid_emails[:5])}")

            valid_roles = ['teacher', 'student']
            invalid_roles = df[~df['role'].isin(valid_roles)]['role'].unique()
            if len(invalid_roles) > 0:
                raise ValueError(f"Invalid role(s): {', '.join(invalid_roles)}. Valid roles are: {', '.join(valid_roles)}")

            return df

        except Exception as e:
            raise ValueError(f"Error parsing file: {str(e)}")

    def start_bulk_invite(
        self, db: Session, file_content: bytes, filename: str,
        bulk_invite_request: BulkInviteRequest, school: School,
        current_user_context: UserContext
    ) -> str:
        try:
            df = self.parse_invite_file(file_content, filename)

            task_id = str(uuid.uuid4())
            task_status = BulkInviteStatus(
                task_id=task_id,
                status="processing",
                total_rows=len(df),
                processed_rows=0,
                successful_invites=0,
                failed_invites=0,
                results=[],
                created_at=datetime.now()
            )

            self._bulk_invite_tasks[task_id] = task_status

            # For now, we'll process synchronously. In production, use background tasks
            self._process_bulk_invites(db, df, bulk_invite_request, school, current_user_context, task_id)

            return task_id

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to start bulk invite: {str(e)}"
            )

    def _process_bulk_invites(
        self, db: Session, df: pd.DataFrame, bulk_invite_request: BulkInviteRequest,
        school: School, current_user_context: UserContext, task_id: str
    ):
        """Process bulk invites and update task status."""
        task_status = self._bulk_invite_tasks[task_id]
        results = []

        try:
            for index, row in df.iterrows():
                row_number = index + 2  # +2 because pandas is 0-indexed and Excel starts at 1, plus header
                try:
                    invite_data = UserInvite(
                        email=row['email'],
                        full_name=row['full_name'],
                        role_name=RoleEnum(row['role']),
                        course_ids=bulk_invite_request.course_ids,
                        level=bulk_invite_request.level
                    )

                    from sqlalchemy import exc
                    try:
                        invited_user = self.invite_user(
                            db, invite_in=invite_data,
                            current_user_context=current_user_context
                        )
                        db.commit()

                        result = BulkInviteResult(
                            row_number=row_number,
                            email=row['email'],
                            full_name=row['full_name'],
                            role_name=RoleEnum(row['role']),
                            status="success",
                            message="User invited successfully",
                            user_id=invited_user.id
                        )
                        task_status.successful_invites += 1

                    except exc.IntegrityError as e:
                        db.rollback()
                        result = BulkInviteResult(
                            row_number=row_number,
                            email=row['email'],
                            full_name=row['full_name'],
                            role_name=RoleEnum(row['role']) if row['role'] in ['teacher', 'student'] else RoleEnum.STUDENT,
                            status="error",
                            message="User already exists or association already exists",
                            user_id=None
                        )
                        task_status.failed_invites += 1

                    except HTTPException as e:
                        db.rollback()
                        result = BulkInviteResult(
                            row_number=row_number,
                            email=row['email'],
                            full_name=row['full_name'],
                            role_name=RoleEnum(row['role']) if row['role'] in ['teacher', 'student'] else RoleEnum.STUDENT,
                            status="error",
                            message=e.detail,
                            user_id=None
                        )
                        task_status.failed_invites += 1

                    except Exception as e:
                        db.rollback()
                        result = BulkInviteResult(
                            row_number=row_number,
                            email=row['email'],
                            full_name=row['full_name'],
                            role_name=RoleEnum(row['role']) if row['role'] in ['teacher', 'student'] else RoleEnum.STUDENT,
                            status="error",
                            message=f"Unexpected error: {str(e)}",
                            user_id=None
                        )
                        task_status.failed_invites += 1

                except Exception as e:
                    result = BulkInviteResult(
                        row_number=row_number,
                        email=row['email'] if 'email' in row else 'N/A',
                        full_name=row['full_name'] if 'full_name' in row else 'N/A',
                        role_name=RoleEnum.STUDENT,
                        status="error",
                        message=f"Row processing error: {str(e)}",
                        user_id=None
                    )
                    task_status.failed_invites += 1

                results.append(result)
                task_status.processed_rows += 1

            task_status.status = "completed"
            task_status.results = results
            task_status.completed_at = datetime.now()

        except Exception as e:
            task_status.status = "failed"
            task_status.error_message = str(e)
            task_status.completed_at = datetime.now()

    def get_bulk_invite_status(self, task_id: str) -> BulkInviteStatus:
        """Get the status of a bulk invite task."""
        if task_id not in self._bulk_invite_tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bulk invite task not found"
            )

        return self._bulk_invite_tasks[task_id]

    def delete_user_by_admin(self, db: Session, user_id: int) -> UserSchema:
        """Delete a user by admin (soft delete)."""
        user = crud_user.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        deleted_user = crud_user.delete(db, id=user_id)

        logger.info(f"User deleted by admin: {user.email}")

        return UserSchema.model_validate(deleted_user)

user_service = UserService()
