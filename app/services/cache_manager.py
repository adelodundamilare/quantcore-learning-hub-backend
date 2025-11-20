"""High-level cache management and monitoring"""
from typing import Dict, Any, List
from datetime import datetime
import logging

from app.utils.cache import get, set, delete, clear
from app.utils.cache_invalidation import cache_invalidator

logger = logging.getLogger(__name__)

class CacheManager:
    """High-level cache management interface"""
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache statistics and performance info"""
        # This is a placeholder - extend based on your cache backend
        return {
            "backend": "memory",
            "status": "active",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def warm_user_cache(user_id: int):
        """Pre-warm critical cache entries for a user"""
        from app.services.cached_user import cached_user_service
        from app.services.cached_trading import cached_trading_service
        from app.core.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Pre-load user profile
            cached_user_service.get_user_profile(db, user_id)
            
            # Pre-load user contexts
            cached_user_service.get_user_contexts(db, user_id)
            
            logger.info(f"Warmed cache for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to warm cache for user {user_id}: {e}")
        finally:
            db.close()
    
    @staticmethod
    def clear_expired_cache():
        """Clear expired cache entries (for memory backend)"""
        # This is automatically handled by the fixed cache implementation
        logger.info("Cache cleanup completed")
    
    @staticmethod
    def invalidate_related_cache(entity_type: str, entity_id: int, **kwargs):
        """Invalidate cache based on entity type and relationships"""
        if entity_type == "user":
            cache_invalidator.invalidate_user_cache(entity_id, kwargs.get('email'))
        elif entity_type == "school":
            cache_invalidator.invalidate_school_cache(entity_id)
        elif entity_type == "course":
            cache_invalidator.invalidate_course_cache(entity_id, kwargs.get('school_id'))
        elif entity_type == "trading":
            cache_invalidator.invalidate_trading_cache(entity_id)
        else:
            logger.warning(f"Unknown entity type for cache invalidation: {entity_type}")

cache_manager = CacheManager()