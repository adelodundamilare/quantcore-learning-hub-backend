import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.cache import cache
from app.core.cache_config import INVALIDATION_PATTERNS

logger = logging.getLogger(__name__)

class CacheService:

    @staticmethod
    async def _invalidate_patterns(patterns: list):
        for pattern in patterns:
            deleted = await cache.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted} cache entries for pattern {pattern}")

    @staticmethod
    async def invalidate_user_cache(user_id: int):
        patterns = [pattern.format(user_id) for pattern in INVALIDATION_PATTERNS["user_update"]]
        await CacheService._invalidate_patterns(patterns)

    @staticmethod
    async def invalidate_course_cache(course_id: int, school_id: Optional[int] = None):
        patterns = [pattern.format(course_id) for pattern in INVALIDATION_PATTERNS["course_update"]]
        if school_id:
            patterns.extend([pattern.format(school_id) for pattern in INVALIDATION_PATTERNS["school_update"] if "courses:school" in pattern])
        await CacheService._invalidate_patterns(patterns)

    @staticmethod
    async def invalidate_school_cache(school_id: int):
        patterns = [pattern.format(school_id) for pattern in INVALIDATION_PATTERNS["school_update"]]
        await CacheService._invalidate_patterns(patterns)

    @staticmethod
    async def invalidate_trading_cache(user_id: int):
        patterns = [pattern.format(user_id) for pattern in INVALIDATION_PATTERNS["trade_execution"]]
        await CacheService._invalidate_patterns(patterns)

    @staticmethod
    async def invalidate_stock_cache(symbol: Optional[str] = None):
        if symbol:
            patterns = [pattern.format(symbol) for pattern in INVALIDATION_PATTERNS["stock_update"]]
        else:
            patterns = INVALIDATION_PATTERNS["stock_update"]
        await CacheService._invalidate_patterns(patterns)

    @staticmethod
    async def warm_cache_for_user(user_id: int):
        try:
            from app.crud.user import user as user_crud
            from app.core.database import SessionLocal

            db = SessionLocal()
            try:
                user = user_crud.get(db, id=user_id)
                if user:
                    contexts = user_crud.get_user_contexts(db, user_id=user_id)
                    await cache.set(f"user:contexts:{user_id}", contexts, ttl=300)

                    logger.info(f"Warmed cache for user {user_id}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to warm cache for user {user_id}: {e}")

    @staticmethod
    async def get_cache_stats() -> Dict[str, Any]:
        try:
            stats = {
                "backend": "Redis" if hasattr(cache.backend, 'redis') else "Memory",
                "timestamp": datetime.utcnow().isoformat()
            }

            if hasattr(cache.backend, 'redis'):
                info = await cache.backend.redis.info()
                stats.update({
                    "redis_version": info.get("redis_version"),
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_ratio": round(
                        info.get("keyspace_hits", 0) / max(
                            (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)), 1
                        ), 4
                    )
                })
            else:
                cache_size = len(cache.backend._cache)
                stats.update({
                    "memory_cache_size": cache_size,
                    "cache_entries": list(cache.backend._cache.keys())[:10]
                })

            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}

    @staticmethod
    async def health_check() -> bool:
        try:
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.utcnow().isoformat()}

            await cache.set(test_key, test_value, ttl=10)
            retrieved = await cache.get(test_key)
            await cache.delete(test_key)

            return retrieved == test_value
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False

cache_service = CacheService()