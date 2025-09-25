from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Delegates handling of Pydantic validation errors to FastAPI's default handler
    to ensure a correctly formatted 422 response.
    """
    return await request_validation_exception_handler(request, exc)

async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled Exception: {exc}")  # Log the full error

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )