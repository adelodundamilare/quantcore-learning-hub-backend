"""Cache invalidation utilities for maintaining data consistency"""
from typing import List, Optional
import logging

from app.utils.cache import delete

logger = logging.getLogger(__name__)

class CacheInvalidator:
    """Centralized cache invalidation for data consistency"""
    
    @staticmethod
    def invalidate_user_cache(user_id: int, email: Optional[str] = None):
        """Invalidate all user-related cache entries"""
        patterns = [
            f"user:profile:{user_id}",
            f"user:contexts:{user_id}",
            f"balance:user:{user_id}",
            f"portfolio:user:{user_id}:*",
            f"watchlists:user:{user_id}:*", 
            f"trades:user:{user_id}:*",
            f"trading_summary_{user_id}",
            f"courses:user:{user_id}:*"
        ]
        
        if email:
            patterns.append(f"user:by_email:{email.lower()}")
        
        _delete_cache_patterns(patterns)
        logger.info(f"Invalidated cache for user {user_id}")
    
    @staticmethod
    def invalidate_school_cache(school_id: int):
        """Invalidate school-related cache entries"""
        patterns = [
            f"school:details:{school_id}",
            f"school:students:{school_id}:*",
            f"school:teachers:{school_id}:*",
            f"courses:school:{school_id}:*",
            f"school:list:*"
        ]
        
        _delete_cache_patterns(patterns)
        logger.info(f"Invalidated cache for school {school_id}")
    
    @staticmethod
    def invalidate_course_cache(course_id: int, school_id: Optional[int] = None):
        """Invalidate course-related cache entries"""
        patterns = [
            f"course:details:{course_id}",
            f"courses:all:*",
        ]
        
        if school_id:
            patterns.extend([
                f"courses:school:{school_id}:*",
                f"school:*:{school_id}:*"
            ])
        
        _delete_cache_patterns(patterns)
        logger.info(f"Invalidated cache for course {course_id}")
    
    @staticmethod
    def invalidate_trading_cache(user_id: int):
        """Invalidate trading-specific cache entries"""
        patterns = [
            f"balance:user:{user_id}",
            f"portfolio:user:{user_id}:*",
            f"watchlists:user:{user_id}:*",
            f"trades:user:{user_id}:*",
            f"trading_summary_{user_id}"
        ]
        
        _delete_cache_patterns(patterns)
        logger.info(f"Invalidated trading cache for user {user_id}")

def _delete_cache_patterns(patterns: List[str]):
    """Helper to delete multiple cache patterns"""
    deleted_count = 0
    for pattern in patterns:
        try:
            if delete(pattern):
                deleted_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete cache pattern {pattern}: {e}")
    
    logger.debug(f"Deleted {deleted_count} cache entries")

# Convenience instance
cache_invalidator = CacheInvalidator()