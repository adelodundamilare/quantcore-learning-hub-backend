import functools
from typing import Optional, Callable, Any
from app.core.cache import cache
from app.core.config import settings


def cache_endpoint(ttl: int = 300, key_prefix: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not settings.CACHE_ENABLED:
                return await func(*args, **kwargs)
            
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not settings.CACHE_ENABLED:
                return func(*args, **kwargs)
            
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            return func(*args, **kwargs)
        
        if _is_async_function(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict, prefix: Optional[str] = None) -> str:
    user_id = None
    context = kwargs.get('context')
    if context and hasattr(context, 'user'):
        user_id = context.user.id
    
    if user_id:
        if prefix:
            key_parts = [f"user:{user_id}:{prefix}"]
        else:
            key_parts = [f"user:{user_id}:{func_name}"]
    else:
        if prefix:
            key_parts = [prefix]
        else:
            key_parts = [func_name]
    
    for arg in args:
        if hasattr(arg, '__dict__'):
            continue
        key_parts.append(str(arg))
    
    if kwargs:
        skip_keys = {'context', 'db', 'current_user', 'current_user_with_context'}
        sorted_kwargs = sorted(kwargs.items())
        for k, v in sorted_kwargs:
            if k not in skip_keys and not isinstance(v, (Callable, type)):
                key_parts.append(f"{k}={v}")
    
    return ":".join(key_parts)


def _is_async_function(func: Callable) -> bool:
    import asyncio
    import inspect
    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)
