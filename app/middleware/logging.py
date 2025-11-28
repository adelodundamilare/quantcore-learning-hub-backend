import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from app.core.cache import cache

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        path = request.url.path
        method = request.method
        
        try:
            response = await call_next(request)
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] {method} {path} - ERROR",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(process_time * 1000, 2),
                    "error": str(exc)
                }
            )
            raise
        
        process_time = time.time() - start_time
        status_code = response.status_code
        
        cache_status = getattr(request.state, "cache_status", None)
        cache_msg = f" [CACHE: {cache_status}]" if cache_status else ""
        
        log_level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"[{request_id}] {method} {path} - {status_code}{cache_msg}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(process_time * 1000, 2),
                "cache_status": cache_status
            }
        )
        
        if isinstance(response, StreamingResponse):
            response.headers["X-Request-ID"] = request_id
        else:
            response.headers["X-Request-ID"] = request_id
        
        return response
