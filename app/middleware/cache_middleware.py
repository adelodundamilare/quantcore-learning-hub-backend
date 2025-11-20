from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging

logger = logging.getLogger(__name__)

class CacheMetricsMiddleware(BaseHTTPMiddleware):
    
    def __init__(self, app, cache_stats: dict = None):
        super().__init__(app)
        self.cache_stats = cache_stats or {
            "hits": 0,
            "misses": 0,
            "requests": 0,
            "avg_response_time": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        self.cache_stats["requests"] += 1
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        self.cache_stats["avg_response_time"] = (
            (self.cache_stats["avg_response_time"] * (self.cache_stats["requests"] - 1) + process_time) 
            / self.cache_stats["requests"]
        )
        
        response.headers["X-Cache-Stats"] = f"hits:{self.cache_stats['hits']},misses:{self.cache_stats['misses']}"
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

class CacheHeaderMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        if hasattr(request.state, "cache_hit"):
            response.headers["X-Cache"] = "HIT" if request.state.cache_hit else "MISS"
        
        if hasattr(request.state, "cache_key"):
            response.headers["X-Cache-Key"] = request.state.cache_key
        
        return response