from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.token_denylist import TokenDenylist
from app.schemas.token_denylist import TokenDenylistCreate
from typing import Optional

class CRUDTokenDenylist(CRUDBase[TokenDenylist, TokenDenylistCreate, None]):
    def get_by_jti(self, db: Session, *, jti: str) -> Optional[TokenDenylist]:
        return db.query(self.model).filter(self.model.jti == jti).first()

token_denylist = CRUDTokenDenylist(TokenDenylist)
