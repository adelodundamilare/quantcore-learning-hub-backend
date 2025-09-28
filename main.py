
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.endpoints import auth, account, course, utility, school, role, permission, notification
from fastapi.exceptions import RequestValidationError
from app.middleware.exceptions import global_exception_handler, validation_exception_handler


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(school.router, prefix="/schools", tags=["Schools"])
app.include_router(account.router, prefix="/account", tags=["Account"])
app.include_router(notification.router, prefix="/notifications", tags=["Notifications"])
app.include_router(course.router, prefix="/courses", tags=["Courses"])

# Routers for new models
app.include_router(role.router, prefix="/roles", tags=["Roles"])
app.include_router(permission.router, prefix="/permissions", tags=["Permissions"])
app.include_router(utility.router, prefix="/utility", tags=["utility"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)