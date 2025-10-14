# Quantcore Learning Hub API

This project is a learning management system (LMS) API built with FastAPI.

## Features

- User Authentication (JWT)
- Role-Based Access Control (RBAC)
- Multi-tenancy (Schools)
- Course Management
- Exam and Question Management
- Exam Attempt Tracking
- Student Exam Statistics
- Role and Permission Management for Super Admins

## Getting Started

(Add installation and setup instructions here)

## Authentication and Authorization

This API uses JWT for authentication. Once authenticated, user permissions are managed via a Role-Based Access Control (RBAC) system.

### Permission Checks

To ensure that only authorized users can perform specific actions, endpoints are protected using a `require_permission` dependency. This dependency checks if the authenticated user's role has the necessary permission to access the endpoint.

#### How it Works

1.  **Super Admin Bypass:** Users with the `SUPER_ADMIN` role automatically bypass all permission checks, granting them full access to all functionalities.
2.  **Role-Based Permissions:** For all other roles (e.g., `ADMIN`, `MEMBER`, `SCHOOL_ADMIN`, `TEACHER`, `STUDENT`), the system checks the permissions explicitly assigned to their role in the database.

#### Usage

To protect an endpoint, simply add `Depends(deps.require_permission(PermissionEnum.<YOUR_PERMISSION>))` to its `dependencies` list. Replace `<YOUR_PERMISSION>` with the specific permission required from `app.core.constants.PermissionEnum`.

**Example (Protecting the `create_course` endpoint):**

```python
from fastapi import APIRouter, Depends, status
from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.course import Course, CourseCreate
from app.services.course import course_service
from app.schemas.user import UserContext
from app.core.constants import PermissionEnum

router = APIRouter()

@router.post("/", response_model=APIResponse[Course], status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(deps.require_permission(PermissionEnum.CREATE_COURSE))])
def create_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_in: CourseCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_course = course_service.create_course(db, course_in=course_in, current_user_context=context)
    return APIResponse(message="Course created successfully", data=Course.model_validate(new_course))
```

## API Endpoints

(Add details about major API endpoints here)

## Database Migrations

(Add Alembic migration instructions here)
