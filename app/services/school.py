from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings

from app.crud.school import school as crud_school
from app.crud.user import user as crud_user
from app.crud.role import role as crud_role
from app.crud.course import course as crud_course
from app.schemas.school import SchoolCreate, AdminSchoolDataSchema
from app.schemas.user import UserCreate, UserContext
from app.crud.base import PaginatedResponse
import math
from app.models.school import School
from app.core.security import get_password_hash
from app.core.constants import RoleEnum
from app.services.email import EmailService
from app.services.notification import notification_service
from app.crud.one_time_token import one_time_token as crud_one_time_token
from app.models.one_time_token import TokenType
import random

class SchoolService:

    async def create_school_and_admin(
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

            hashed_password = get_password_hash(admin_in.password)

            admin_create_data = {
                "full_name": admin_in.full_name,
                "email": admin_in.email,
                "hashed_password": hashed_password,
                "is_active": False
            }

            new_admin = crud_user.create(db, obj_in=admin_create_data, commit=False)
            crud_user.add_user_to_school(
                db, user=new_admin, school=new_school, role=school_admin_role
            )

            verification_code = str(random.randint(1000, 9999))
            expires_at = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)

            crud_one_time_token.create(
                db,
                obj_in={
                    "user_id": new_admin.id,
                    "token": verification_code,
                    "token_type": TokenType.ACCOUNT_VERIFICATION,
                    "expires_at": expires_at,
                },
                commit=False
            )

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during the signup process: {e}",
            )

        await EmailService.send_email(
            to_email=new_admin.email,
            subject=f"Welcome! Verify Your Account",
            template_name="verify_account.html",
            template_context={
                'user_name': new_admin.full_name,
                'verification_code': verification_code
            }
        )
        notification_service.create_notification(
            db,
            user_id=new_admin.id,
            message=f"Welcome! Your school {new_school.name} has been created. Please verify your account.",
            notification_type="account_verification",
            link=f"/verify-account"
        )

        return new_school

    def get_admin_schools_report(self, db: Session, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> PaginatedResponse[AdminSchoolDataSchema]:
        if not current_user_context.role or current_user_context.role.name != RoleEnum.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can access this report.")

        schools_data = crud_school.get_admin_school_data(db, skip=skip, limit=limit)

        total_schools = crud_school.get_all_schools_count(db)

        page = (skip // limit) + 1 if limit > 0 else 1
        pages = math.ceil(total_schools / limit) if limit > 0 else 0
        has_next = (skip + limit) < total_schools
        has_previous = skip > 0

        return PaginatedResponse(
            items=[AdminSchoolDataSchema(**school_data._asdict()) for school_data in schools_data],
            total=total_schools,
            page=page,
            size=limit,
            pages=pages,
            has_next=has_next,
            has_previous=has_previous
        )

    def get_all_schools_admin(self, db: Session, skip: int = 0, limit: int = 100) -> list[School]:
        """Get all schools for super admin management."""
        return crud_school.get_multi(db=db, skip=skip, limit=limit)

    def update_school_admin(self, db: Session, school_id: int, school_in) -> School:
        """Update school details by super admin."""
        school = crud_school.get(db=db, id=school_id)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        updated = crud_school.update(db=db, db_obj=school, obj_in=school_in)
        from app.utils.cache import delete
        delete(f"school:details:{school_id}")
        delete(f"school:students:{school_id}:0:100")
        delete(f"school:teachers:{school_id}:0:100")
        delete(f"courses:school:{school_id}:0:100")
        return updated

    def delete_school_admin(self, db: Session, school_id: int) -> School:
        """Soft delete a school by super admin."""
        school = crud_school.get(db=db, id=school_id)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

        if school.deleted_at:
            raise HTTPException(status_code=400, detail="School is already deleted")

        courses = crud_course.get_courses_by_school(db, school_id=school_id)
        for course in courses:
            crud_course.bulk_soft_delete_related_entities(db, course.id)

        crud_school.bulk_soft_delete_related_entities(db, school_id)

        result = crud_school.delete(db=db, id=school_id)
        from app.utils.cache import delete
        delete(f"school:details:{school_id}")
        delete(f"school:students:{school_id}:0:100")
        delete(f"school:teachers:{school_id}:0:100")
        delete(f"courses:school:{school_id}:0:100")
        return result

school_service = SchoolService()
