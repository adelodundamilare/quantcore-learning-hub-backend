from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """CRUD operations for Permissions."""
    pass

permission = CRUDPermission(Permission)
