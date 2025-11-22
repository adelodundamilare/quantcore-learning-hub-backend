from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging

from app.crud.school import school as school_crud
from app.crud.user import user as user_crud
from app.core.decorators import cache_school_data
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class CachedSchoolService:

    @cache_school_data(ttl=900)
    async def get_school_details(self, db: Session, school_id: int) -> Optional[Dict[str, Any]]:
        school = school_crud.get(db, id=school_id)
        if not school:
            return None

        return {
            "id": school.id,
            "name": school.name,
            "domain": getattr(school, 'domain', None),
            "is_active": getattr(school, 'is_active', True),
            "created_at": school.created_at.isoformat() if school.created_at else None,
            "updated_at": school.updated_at.isoformat() if school.updated_at else None
        }

    @cache_school_data(ttl=300)
    async def get_school_students(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        students = user_crud.get_multi_by_school_and_role(
            db, school_id=school_id, role_name="student", skip=skip, limit=limit
        )

        return [
            {
                "id": student.id,
                "email": student.email,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "full_name": student.full_name,
                "is_active": student.is_active
            }
            for student in students
        ]

    @cache_school_data(ttl=300)
    async def get_school_teachers(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        teachers = user_crud.get_multi_by_school_and_role(
            db, school_id=school_id, role_name="teacher", skip=skip, limit=limit
        )

        return [
            {
                "id": teacher.id,
                "email": teacher.email,
                "first_name": teacher.first_name,
                "last_name": teacher.last_name,
                "full_name": teacher.full_name,
                "is_active": teacher.is_active
            }
            for teacher in teachers
        ]

    @cache_school_data(ttl=600)
    async def get_schools_list(self, db: Session, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        schools = school_crud.get_multi(db, skip=skip, limit=limit)

        return [
            {
                "id": school.id,
                "name": school.name,
                "domain": getattr(school, 'domain', None),
                "is_active": getattr(school, 'is_active', True),
                "student_count": len(getattr(school, 'students', [])),
                "teacher_count": len(getattr(school, 'teachers', []))
            }
            for school in schools
        ]

    async def invalidate_school_cache(self, school_id: int):
        await cache_service.invalidate_school_cache(school_id)

cached_school_service = CachedSchoolService()