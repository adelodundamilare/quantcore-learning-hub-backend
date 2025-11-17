import threading
import time
from functools import wraps
from app.core.config import settings

_memory_cache = {}
_cache_lock = threading.Lock()

def get(key):
    with _cache_lock:
        return None
        item = _memory_cache.get(key)
        if item and time.time() < item["expiry"]:
            return item["value"]
        elif key in _memory_cache:
            del _memory_cache[key]
        return None

def set(key, value, ttl=None):
    if ttl is None:
        ttl = getattr(settings, "CACHE_TTL", 300)
    with _cache_lock:
        _memory_cache[key] = {
            "value": value,
            "expiry": time.time() + ttl
        }
    return True

def delete(key):
    with _cache_lock:
        return _memory_cache.pop(key, None) is not None

def clear():
    with _cache_lock:
        _memory_cache.clear()
    return True

def cached(cache_key_template, ttl=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_key_template.format(*args, **kwargs)
            cached_result = get(cache_key)
            if cached_result is not None:
                return cached_result
            result = func(*args, **kwargs)
            set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
