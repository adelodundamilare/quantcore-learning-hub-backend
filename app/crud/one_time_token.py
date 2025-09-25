from app.crud.base import CRUDBase
from app.models.one_time_token import OneTimeToken
from app.schemas.one_time_token import OneTimeTokenCreate

class CRUDOneTimeToken(CRUDBase[OneTimeToken, OneTimeTokenCreate, object]):
    """CRUD operations for OneTimeTokens."""
    pass

one_time_token = CRUDOneTimeToken(OneTimeToken)
