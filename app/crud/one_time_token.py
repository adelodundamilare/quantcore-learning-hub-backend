from app.crud.base import CRUDBase
from app.models.one_time_token import OneTimeToken, TokenType
from app.schemas.one_time_token import OneTimeTokenCreate
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

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

    def delete_by_user_id_and_type(self, db: Session, *, user_id: int, token_type: TokenType) -> None:
        db.query(OneTimeToken).filter(
            OneTimeToken.user_id == user_id,
            OneTimeToken.token_type == token_type
        ).delete()
        db.commit()

one_time_token = CRUDOneTimeToken(OneTimeToken)
