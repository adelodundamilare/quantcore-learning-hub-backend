from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from app.utils.deps import get_current_super_admin
from app.schemas.response import APIResponse
from app.services.cache_service import cache_service
from app.core.cache import cache

router = APIRouter()

@router.get("/cache/stats")
async def get_cache_stats(
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Get cache statistics and health info"""
    try:
        stats = await cache_service.get_cache_stats()
        return APIResponse(
            message="Cache statistics retrieved",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@router.post("/cache/clear")
async def clear_cache(
    patterns: Optional[List[str]] = None,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Clear cache entries by pattern or clear all"""
    try:
        if patterns:
            cleared_count = 0
            for pattern in patterns:
                count = await cache.delete_pattern(pattern)
                cleared_count += count
            message = f"Cleared {cleared_count} cache entries matching patterns: {patterns}"
        else:
            await cache.clear()
            message = "All cache entries cleared"

        return APIResponse(message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.post("/cache/invalidate/user/{user_id}")
async def invalidate_user_cache(
    user_id: int,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Invalidate all cache entries for a specific user"""
    try:
        await cache_service.invalidate_user_cache(user_id)
        return APIResponse(message=f"Cache invalidated for user {user_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate user cache: {str(e)}")

@router.post("/cache/invalidate/course/{course_id}")
async def invalidate_course_cache(
    course_id: int,
    school_id: Optional[int] = None,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Invalidate cache entries for a specific course"""
    try:
        await cache_service.invalidate_course_cache(course_id, school_id)
        return APIResponse(message=f"Cache invalidated for course {course_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate course cache: {str(e)}")

@router.post("/cache/invalidate/school/{school_id}")
async def invalidate_school_cache(
    school_id: int,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Invalidate cache entries for a specific school"""
    try:
        await cache_service.invalidate_school_cache(school_id)
        return APIResponse(message=f"Cache invalidated for school {school_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate school cache: {str(e)}")

@router.post("/cache/invalidate/stocks")
async def invalidate_stock_cache(
    symbol: Optional[str] = None,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Invalidate stock data cache"""
    try:
        await cache_service.invalidate_stock_cache(symbol)
        message = f"Stock cache invalidated for {symbol}" if symbol else "All stock cache invalidated"
        return APIResponse(message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate stock cache: {str(e)}")

@router.post("/cache/warm/user/{user_id}")
async def warm_user_cache(
    user_id: int,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """Pre-warm cache for a specific user"""
    try:
        await cache_service.warm_cache_for_user(user_id)
        return APIResponse(message=f"Cache warmed for user {user_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to warm user cache: {str(e)}")

@router.get("/cache/health")
async def cache_health_check() -> APIResponse:
    """Check cache health status"""
    try:
        is_healthy = await cache_service.health_check()
        status = "healthy" if is_healthy else "unhealthy"
        return APIResponse(
            message=f"Cache is {status}",
            data={"healthy": is_healthy}
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cache health check failed: {str(e)}")

@router.get("/cache/keys")
async def list_cache_keys(
    pattern: str = "*",
    limit: int = 100,
    current_user=Depends(get_current_super_admin)
) -> APIResponse:
    """List cache keys matching pattern (Redis only)"""
    try:
        if hasattr(cache.backend, 'redis'):
            keys = []
            count = 0
            async for key in cache.backend.redis.scan_iter(match=pattern):
                if count >= limit:
                    break
                keys.append(key)
                count += 1

            return APIResponse(
                message=f"Found {len(keys)} cache keys",
                data={"keys": keys, "pattern": pattern, "limit": limit}
            )
        else:
            return APIResponse(
                message="Key listing only available with Redis backend",
                data={"backend": "memory"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list cache keys: {str(e)}")