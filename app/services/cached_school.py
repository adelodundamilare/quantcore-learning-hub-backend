from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging

from app.crud.school import school as school_crud
from app.crud.user import user as user_crud
from app.utils.cache import cached

logger = logging.getLogger(__name__)

class CachedSchoolService:
    """School service with strategic caching"""
    
    @cached("school:details:{}", ttl=900)  # 15 minutes cache
    def get_school_details(self, db: Session, school_id: int) -> Optional[Dict[str, Any]]:
        """Get school details with caching"""
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
    
    @cached("school:students:{}:{}:{}", ttl=300)  # 5 minutes cache
    def get_school_students(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get school students with caching"""
        # Get students by school through user associations
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
    
    @cached("school:teachers:{}:{}:{}", ttl=300)  # 5 minutes cache
    def get_school_teachers(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get school teachers with caching"""
        # Get teachers by school through user associations
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
    
    @cached("school:list:{}:{}", ttl=600)  # 10 minutes cache
    def get_schools_list(self, db: Session, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get schools list with caching"""
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
    
    def invalidate_school_cache(self, school_id: int):
        """Invalidate school-related cache"""
        from app.utils.cache import delete
        
        # Clear school-specific cache
        delete(f"school:details:{school_id}")
        
        # Clear lists that might include this school
        # Note: This is a simple approach, for production you might want pattern-based deletion
        for skip in [0, 100, 200]:  # Clear common pagination offsets
            delete(f"school:students:{school_id}:{skip}:100")
            delete(f"school:teachers:{school_id}:{skip}:100")
            delete(f"school:list:{skip}:100")
        
        logger.info(f"Cache invalidated for school {school_id}")

cached_school_service = CachedSchoolService()