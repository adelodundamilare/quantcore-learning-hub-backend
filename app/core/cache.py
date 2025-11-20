import json
import asyncio
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
import time
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

class MemoryCacheBackend(CacheBackend):
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            await self._cleanup_expired()
            item = self._cache.get(key)
            if item and (item.get("expiry", 0) == 0 or time.time() < item["expiry"]):
                return item["value"]
            elif key in self._cache:
                del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            expiry = time.time() + (ttl or settings.CACHE_TTL) if ttl != 0 else 0
            self._cache[key] = {
                "value": value,
                "expiry": expiry,
                "created_at": time.time()
            }
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._cache.pop(key, None) is not None

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def _cleanup_expired(self):
        current_time = time.time()
        expired_keys = [
            key for key, item in self._cache.items()
            if item.get("expiry", 0) > 0 and current_time >= item["expiry"]
        ]
        for key in expired_keys:
            del self._cache[key]

class RedisCacheBackend(CacheBackend):
    def __init__(self, redis_url: str):
        import redis.asyncio as redis
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            return self._deserialize(value) if value else None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = self._serialize(value)
            if ttl is None:
                ttl = settings.CACHE_TTL
            if ttl == 0:
                await self.redis.set(key, serialized)
            else:
                await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        try:
            await self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

def create_cache_backend() -> CacheBackend:
    if settings.REDIS_URL:
        try:
            logger.info("Initializing Redis cache backend")
            return RedisCacheBackend(settings.REDIS_URL)
        except ImportError:
            logger.warning("Redis not available, falling back to memory cache")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}, falling back to memory cache")

    logger.info("Using in-memory cache backend")
    return MemoryCacheBackend()

cache_backend = create_cache_backend()

class CacheManager:
    def __init__(self, backend: CacheBackend):
        self.backend = backend

    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        key_data = f"{prefix}:{':'.join(map(str, args))}"
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_data += f":{':'.join(f'{k}={v}' for k, v in sorted_kwargs)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return await self.backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        return await self.backend.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        if isinstance(self.backend, RedisCacheBackend):
            try:
                keys = []
                async for key in self.backend.redis.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    return await self.backend.redis.delete(*keys)
                return 0
            except Exception as e:
                logger.error(f"Redis pattern delete error: {e}")
                return 0
        else:
            count = 0
            import fnmatch
            async with self.backend._lock:
                keys_to_delete = [
                    key for key in self.backend._cache.keys()
                    if fnmatch.fnmatch(key, pattern)
                ]
                for key in keys_to_delete:
                    del self.backend._cache[key]
                    count += 1
            return count

    async def clear(self) -> bool:
        return await self.backend.clear()

cache = CacheManager(cache_backend)