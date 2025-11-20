import threading
import time
from functools import wraps
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

def get(key: str) -> Optional[Any]:
    """Get item from cache"""
    with _cache_lock:
        _cleanup_expired()
        item = _memory_cache.get(key)
        if item and (item.get("expiry", 0) == 0 or time.time() < item["expiry"]):
            return item["value"]
        elif key in _memory_cache:
            del _memory_cache[key]
        return None

def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set item in cache"""
    if ttl is None:
        ttl = 300

    with _cache_lock:
        expiry = time.time() + ttl if ttl > 0 else 0
        _memory_cache[key] = {
            "value": value,
            "expiry": expiry,
            "created_at": time.time()
        }
    return True

def delete(key: str) -> bool:
    """Delete item from cache"""
    with _cache_lock:
        return _memory_cache.pop(key, None) is not None

def clear() -> bool:
    """Clear all cache"""
    with _cache_lock:
        _memory_cache.clear()
    return True

def _cleanup_expired():
    """Remove expired entries"""
    current_time = time.time()
    expired_keys = [
        key for key, item in _memory_cache.items()
        if item.get("expiry", 0) > 0 and current_time >= item["expiry"]
    ]
    for key in expired_keys:
        del _memory_cache[key]

def cached(cache_key_template: str, ttl: Optional[int] = None):
    """Cache decorator that actually works"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                cache_key = cache_key_template.format(*args, **kwargs)
            except (IndexError, KeyError):
                cache_key = f"{cache_key_template}:{hash(str(args) + str(kwargs))}"

            cached_result = get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return cached_result

            logger.debug(f"Cache MISS for key: {cache_key}")

            try:
                result = func(*args, **kwargs)
                set(cache_key, result, ttl)
                return result
            except Exception as e:
                logger.error(f"Function execution failed: {e}")
                raise
        return wrapper
    return decorator
