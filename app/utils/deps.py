from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.crud.user import user as user_crud
from app.crud.school import school as crud_school
from app.crud.role import role as crud_role
from app.models.user import User
from app.crud.token_denylist import token_denylist as token_denylist_crud
from app.schemas.token import TokenPayload
from app.schemas.user import UserContext

http_bearer = HTTPBearer()

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