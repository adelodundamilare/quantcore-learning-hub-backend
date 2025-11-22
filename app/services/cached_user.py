from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
import logging

from app.crud.user import user as user_crud
from app.core.decorators import cache_user_data
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

class CachedUserService:

    @cache_user_data(ttl=600)
    async def get_user_profile(self, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        user = user_crud.get(db, id=user_id)
        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }

    @cache_user_data(ttl=300)
    async def get_user_contexts(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        contexts = user_crud.get_user_contexts(db, user_id=user_id)

        return [
            {
                "user_id": ctx.user_id,
                "school_id": ctx.school_id,
                "role_id": ctx.role_id,
                "role_name": ctx.role.name if ctx.role else None,
                "school_name": ctx.school.name if ctx.school else None
            }
            for ctx in contexts
        ]

    @cache_user_data(ttl=900)
    async def get_user_by_email(self, db: Session, email: str) -> Optional[Dict[str, Any]]:
        user = user_crud.get_by_email(db, email=email.lower())
        if not user:
            return None

        return await self.get_user_profile(db, user.id)

    async def invalidate_user_cache(self, user_id: int, email: str = None):
        await cache_service.invalidate_user_cache(user_id)

cached_user_service = CachedUserService()