import asyncio
from typing import Dict, Any
from datetime import datetime
import logging

from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class CacheManager:

    @staticmethod
    async def get_cache_stats() -> Dict[str, Any]:
        return await cache_service.get_cache_stats()

    @staticmethod
    async def warm_user_cache(user_id: int):
        await cache_service.warm_cache_for_user(user_id)

    @staticmethod
    async def clear_expired_cache():
        pass

    @staticmethod
    async def invalidate_related_cache(entity_type: str, entity_id: int, **kwargs):
        if entity_type == "user":
            await cache_service.invalidate_user_cache(entity_id)
        elif entity_type == "school":
            await cache_service.invalidate_school_cache(entity_id)
        elif entity_type == "course":
            await cache_service.invalidate_course_cache(entity_id, kwargs.get('school_id'))
        elif entity_type == "trading":
            await cache_service.invalidate_trading_cache(entity_id)
        else:
            logger.warning(f"Unknown entity type for cache invalidation: {entity_type}")

cache_manager = CacheManager()