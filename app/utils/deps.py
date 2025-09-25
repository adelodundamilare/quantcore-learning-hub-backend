from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.crud.user import user as user_crud
from app.crud.school import school as crud_school
from app.crud.role import role as crud_role
from app.models.user import User
from app.crud.token_denylist import token_denylist as token_denylist_crud
from app.schemas.token import TokenPayload
from app.schemas.user import UserContext

from app.schemas.token import TokenPayload
from app.schemas.user import UserContext
from app.core.constants import PermissionEnum

from app.crud.token_denylist import token_denylist as token_denylist_crud
from app.schemas.token import TokenPayload
from app.schemas.user import UserContext

http_bearer = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_transactional_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def require_permission(permission_name: PermissionEnum):
    """Dependency that checks if the current user has the required permission."""
    def _verify_permission(context: UserContext = Depends(get_current_user_with_context)):
        # Super Admin bypasses all checks
        if context.role and context.role.name == "Super Admin":
            return

        if not context.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no assigned role.")

        user_permissions = {p.name for p in context.role.permissions}
        if permission_name.value not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )
    return _verify_permission

async def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )

        jti = payload.get("jti")
        if jti and token_denylist_crud.get_by_jti(db, jti=jti):
            raise HTTPException(status_code=401, detail="Token has been revoked")

        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = user_crud.get_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_current_user_with_context(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> UserContext:
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = user_crud.get(db, id=token_data.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or not active")

    school = crud_school.get(db, id=token_data.school_id) if token_data.school_id else None
    role = crud_role.get(db, id=token_data.role_id) if token_data.role_id else None

    if (token_data.school_id and not school) or (token_data.role_id and not role):
        raise HTTPException(status_code=404, detail="Context not found")

    return UserContext(user=user, school=school, role=role)