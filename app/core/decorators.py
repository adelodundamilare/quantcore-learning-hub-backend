import asyncio
import inspect
from functools import wraps
from typing import Optional, Callable, List
import logging

from app.core.cache import cache

logger = logging.getLogger(__name__)

def cache_result(
    key_prefix: str,
    ttl: Optional[int] = None,
    skip_cache: bool = False,
    invalidate_patterns: Optional[List[str]] = None,
    serialize_args: bool = True
):
    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if skip_cache:
                return await func(*args, **kwargs)

            if serialize_args:
                cache_key = cache.generate_key(key_prefix, *args, **kwargs)
            else:
                cache_key = f"{key_prefix}:default"

            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return cached_result

            logger.debug(f"Cache MISS for key: {cache_key}")

            try:
                result = await func(*args, **kwargs)

                await cache.set(cache_key, result, ttl)

                return result
            except Exception as e:
                logger.error(f"Function execution failed: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if skip_cache:
                return func(*args, **kwargs)

            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if serialize_args:
                cache_key = cache.generate_key(key_prefix, *args, **kwargs)
            else:
                cache_key = f"{key_prefix}:default"

            cached_result = loop.run_until_complete(cache.get(cache_key))
            if cached_result is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return cached_result

            logger.debug(f"Cache MISS for key: {cache_key}")

            try:
                result = func(*args, **kwargs)

                loop.run_until_complete(cache.set(cache_key, result, ttl))

                return result
            except Exception as e:
                logger.error(f"Function execution failed: {e}")
                raise

        return async_wrapper if is_async else sync_wrapper

    return decorator

def invalidate_cache(*patterns: str):
    async def invalidate():
        for pattern in patterns:
            deleted_count = await cache.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")

    return invalidate

def cache_user_data(ttl: int = 300):
    return cache_result("user", ttl=ttl)

def cache_course_data(ttl: int = 600):
    return cache_result("course", ttl=ttl)

def cache_trading_data(ttl: int = 30):
    return cache_result("trading", ttl=ttl)

def cache_stock_data(ttl: int = 60):
    return cache_result("stock", ttl=ttl)

def cache_school_data(ttl: int = 900):
    return cache_result("school", ttl=ttl)

def cache_leaderboard(ttl: int = 300):
    return cache_result("leaderboard", ttl=ttl)

def cache_notifications(ttl: int = 120):
    return cache_result("notifications", ttl=ttl)

def cache_sync_safe(key_prefix: str, ttl: Optional[int] = None):
    """Cache decorator that works with both sync and async functions safely"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

class CacheInvalidationContext:
    def __init__(self, *patterns: str):
        self.patterns = patterns

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:  # Only invalidate if no exception occurred
            for pattern in self.patterns:
                await cache.delete_pattern(pattern)

class CacheKeys:
    USER_PROFILE = "user:profile:{user_id}"
    USER_CONTEXTS = "user:contexts:{user_id}"
    COURSE_LIST = "course:list:{school_id}"
    COURSE_DETAILS = "course:details:{course_id}"
    TRADING_PORTFOLIO = "trading:portfolio:{user_id}"
    TRADING_BALANCE = "trading:balance:{user_id}"
    STOCK_PRICE = "stock:price:{symbol}"
    POPULAR_STOCKS = "stock:popular"
    SCHOOL_STUDENTS = "school:students:{school_id}"
    SCHOOL_TEACHERS = "school:teachers:{school_id}"
    LEADERBOARD_GLOBAL = "leaderboard:global"
    NOTIFICATIONS_USER = "notifications:user:{user_id}"