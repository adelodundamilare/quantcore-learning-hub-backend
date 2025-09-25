from app.crud.base import CRUDBase
from app.models.one_time_token import OneTimeToken, TokenType
from app.schemas.one_time_token import OneTimeTokenCreate
from sqlalchemy.orm import Session
from datetime import datetime

class CRUDOneTimeToken(CRUDBase[OneTimeToken, OneTimeTokenCreate, object]):
    def get_by_token_value(self, db: Session, *, token: str, token_type: TokenType) -> OneTimeToken | None:
        return db.query(OneTimeToken).filter(
            OneTimeToken.token == token,
            OneTimeToken.token_type == token_type,
            OneTimeToken.expires_at > datetime.utcnow()
        ).first()

    def delete_by_token_value(self, db: Session, *, token: str, token_type: TokenType) -> None:
        db.query(OneTimeToken).filter(
            OneTimeToken.token == token,
            OneTimeToken.token_type == token_type
        ).delete()
        db.commit()

one_time_token = CRUDOneTimeToken(OneTimeToken)
