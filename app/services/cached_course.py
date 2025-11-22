from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import logging

from app.core.decorators import cache_course_data, cache_user_data, CacheKeys
from app.services.cache_service import cache_service
from app.crud.course import course as course_crud
from app.crud.user import user as user_crud

logger = logging.getLogger(__name__)

class CachedCourseService:

    @cache_course_data(ttl=600)
    async def get_course_details(self, db: Session, course_id: int) -> Optional[Dict[str, Any]]:
        course = course_crud.get(db, id=course_id)
        if not course:
            return None

        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "level": course.level,
            "school_id": course.school_id,
            "created_at": course.created_at.isoformat() if course.created_at else None,
            "updated_at": course.updated_at.isoformat() if course.updated_at else None
        }

    @cache_course_data(ttl=300)
    async def get_courses_by_school(self, db: Session, school_id: int) -> List[Dict[str, Any]]:
        courses = course_crud.get_by_school(db, school_id=school_id)
        return [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "level": course.level,
                "created_at": course.created_at.isoformat() if course.created_at else None
            }
            for course in courses
        ]

    @cache_user_data(ttl=300)
    async def get_user_courses(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        enrollments = db.query(course_crud.model)\
            .join(course_crud.model.enrollments)\
            .filter(course_crud.model.enrollments.any(user_id=user_id))\
            .all()

        return [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "level": course.level,
                "progress": 0
            }
            for course in enrollments
        ]

    @cache_course_data(ttl=120)
    async def get_course_progress(self, db: Session, user_id: int, course_id: int) -> Dict[str, Any]:
        return {
            "course_id": course_id,
            "user_id": user_id,
            "completed_lessons": 0,
            "total_lessons": 0,
            "progress_percentage": 0.0,
            "last_accessed": None
        }

    async def create_course(self, db: Session, course_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            course = course_crud.create(db, obj_in=course_data)

            await cache_service.invalidate_course_cache(course.id, course.school_id)

            return {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "school_id": course.school_id
            }
        except Exception as e:
            logger.error(f"Course creation failed: {e}")
            raise

    async def update_course(self, db: Session, course_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            course = course_crud.get(db, id=course_id)
            if not course:
                raise ValueError(f"Course {course_id} not found")

            updated_course = course_crud.update(db, db_obj=course, obj_in=update_data)

            await cache_service.invalidate_course_cache(course_id, updated_course.school_id)

            return {
                "id": updated_course.id,
                "title": updated_course.title,
                "description": updated_course.description
            }
        except Exception as e:
            logger.error(f"Course update failed: {e}")
            raise

    async def enroll_user(self, db: Session, user_id: int, course_id: int) -> Dict[str, Any]:
        try:
            await cache_service.invalidate_user_cache(user_id)
            await cache_service.invalidate_course_cache(course_id)

            return {"message": "Enrollment successful"}
        except Exception as e:
            logger.error(f"Course enrollment failed: {e}")
            raise

cached_course_service = CachedCourseService()