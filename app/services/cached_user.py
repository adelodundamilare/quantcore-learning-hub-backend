from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging

from app.crud.user import user as user_crud
from app.utils.cache import cached

logger = logging.getLogger(__name__)

class CachedUserService:
    """User service with strategic caching"""
    
    @cached("user:profile:{}", ttl=600)  # 10 minutes cache
    def get_user_profile(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile with caching"""
        user = user_crud.get(db, id=user_id)
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
    
    @cached("user:contexts:{}", ttl=300)  # 5 minutes cache
    def get_user_contexts(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get user contexts with caching"""
        contexts = user_crud.get_user_contexts(db, user_id=user_id)
        
        return [
            {
                "user_id": ctx.user_id,
                "school_id": ctx.school_id,
                "role_id": ctx.role_id,
                "role_name": ctx.role.name if ctx.role else None,
                "school_name": ctx.school.name if ctx.school else None
            }
            for ctx in contexts
        ]
    
    @cached("user:by_email:{}", ttl=900)  # 15 minutes cache  
    def get_user_by_email(self, db: Session, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email with caching"""
        user = user_crud.get_by_email(db, email=email.lower())
        if not user:
            return None
        
        return self.get_user_profile(db, user.id)
    
    def invalidate_user_cache(self, user_id: int, email: str = None):
        """Invalidate user-related cache"""
        from app.utils.cache import delete
        
        # Clear user-specific cache
        delete(f"user:profile:{user_id}")
        delete(f"user:contexts:{user_id}")
        
        if email:
            delete(f"user:by_email:{email.lower()}")
        
        logger.info(f"Cache invalidated for user {user_id}")

cached_user_service = CachedUserService()