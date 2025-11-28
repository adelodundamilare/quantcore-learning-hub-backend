from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from app.schemas.response import ErrorResponse, ErrorDetail
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

def _get_error_code(status_code: int) -> str:
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
        501: "NOT_IMPLEMENTED",
    }
    return code_map.get(status_code, f"HTTP_{status_code}")

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = str(uuid.uuid4())
    error_response = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"validation_errors": exc.errors()}
        ),
        timestamp=datetime.utcnow().isoformat(),
        path=str(request.url),
        request_id=request_id
    )
    logger.warning(f"[{request_id}] Validation error: {exc.errors()}", extra={"request_id": request_id})
    return JSONResponse(status_code=422, content=error_response.model_dump())

async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    
    if isinstance(exc, HTTPException):
        error_code = _get_error_code(exc.status_code)
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=error_code,
                message=exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            ),
            timestamp=datetime.utcnow().isoformat(),
            path=str(request.url),
            request_id=request_id
        )
        logger.warning(f"[{request_id}] HTTP {exc.status_code}: {exc.detail}", extra={"request_id": request_id})
        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={"error_type": type(exc).__name__}
        ),
        timestamp=datetime.utcnow().isoformat(),
        path=str(request.url),
        request_id=request_id
    )
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True, extra={"request_id": request_id})
    return JSONResponse(status_code=500, content=error_response.model_dump())