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

#### Module-Specific Access Restrictions

Certain modules have specific role-based access restrictions beyond general permissions:

*   **Billing Module:** Access to all endpoints within the `/billing` module is restricted. Users with the `STUDENT` or `TEACHER` role will receive a `403 Forbidden` error when attempting to access any billing-related functionality.

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

This section outlines the various API endpoints and WebSocket events that a frontend application can interact with.

### I. HTTP Endpoints (REST API) - Called by Frontend

These are the standard API endpoints that the frontend would interact with to perform actions like:

*   **Authentication**:
    *   `POST /auth/login`: To get a JWT token.
    *   `POST /auth/register`: To create a new user.
    *   (and other auth-related endpoints like password reset, token refresh, etc., which are typically handled by `app/endpoints/auth.py` and `app/endpoints/account.py`).

*   **Stock Data**:
    *   `GET /trading/stocks`: To get a list of all stocks (e.g., for a search bar or stock listing).
    *   `GET /trading/stocks/{ticker}/details_combined`: To get comprehensive details for a specific stock.

### II. WebSocket Events - Emitted by Frontend / Listened to by Frontend

These are the events that the frontend would send to or receive from the WebSocket server (`app/realtime/websockets.py`).

**Events Emitted by Frontend (Frontend calls these)**:

*   **`connect`**: (Implicitly handled by the Socket.IO client library when `io()` is called). This establishes the connection and sends the authentication token.
*   **`subscribe`**: Sent by the frontend to subscribe to real-time updates for a specific stock symbol.
    *   **Data**: `{ symbol: 'AAPL' }`
*   **`unsubscribe`**: Sent by the frontend to stop receiving real-time updates for a specific stock symbol.
    *   **Data**: `{ symbol: 'AAPL' }`
*   **`ping`**: Sent periodically by the frontend to keep the connection alive and check server responsiveness.
    *   **Data**: `{}` (or any arbitrary data)

**Events Listened to by Frontend (Frontend receives these)**:

*   **`connected`**: Received after a successful WebSocket connection and authentication.
    *   **Data**: `{ status: 'success', message: 'Connected successfully' }`
*   **`price_update`**: Received when there's a new price update for a subscribed stock symbol.
    *   **Data**: `{ symbol: 'AAPL', data: { price: 175.00, change: 1.50, ... } }` (the `data` object will contain the full quote from `polygon_service.get_latest_quote`)
*   **`subscribed`**: Received after a successful subscription request.
    *   **Data**: `{ symbol: 'AAPL', status: 'success' }`
*   **`unsubscribed`**: Received after a successful unsubscription request.
    *   **Data**: `{ symbol: 'AAPL', status: 'success' }`
*   **`error`**: Received if there's an error related to the WebSocket connection, authentication, or a specific subscription.
    *   **Data**: `{ message: 'Error details', symbol: 'AAPL' (optional) }`
*   **`pong`**: Received in response to a `ping` event.
    *   **Data**: `{ timestamp: '...' }`

## Database Migrations

This project uses Alembic for database migrations. Follow these steps to manage your database schema:

### 1. Generate a new migration script

After making changes to your SQLAlchemy models (e.g., `app/models/*.py`), you need to generate a new migration script. Alembic will automatically detect changes and create a script.

```bash
alembic revision --autogenerate -m "Descriptive message about your changes"
```

Replace `"Descriptive message about your changes"` with a brief, meaningful description of the changes you've made.

### 2. Apply migrations

To apply pending migrations to your database, use the `upgrade` command:

```bash
alembic upgrade head
```

This will apply all migration scripts that have not yet been applied to your database, bringing it up to the latest version.

### 3. Downgrade migrations (if needed)

If you need to revert a migration (e.g., during development or to fix an issue), you can use the `downgrade` command. To revert the last applied migration:

```bash
alembic downgrade -1
```

To downgrade to a specific revision:

```bash
alembic downgrade <revision_id>
```

Use `alembic history` to view past revision IDs.
