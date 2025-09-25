"""insert new permissions

Revision ID: aca92d4f646a
Revises: 9eb517682281
Create Date: 2025-09-25 15:36:28.806593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.core.constants import PermissionEnum

# revision identifiers, used by Alembic.
revision: str = 'aca92d4f646a'
down_revision: Union[str, None] = '9eb517682281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    permissions_table = sa.table('permissions', sa.column('name', sa.String))

    # Get existing permissions from the database
    conn = op.get_bind()
    existing_permissions = [r[0] for r in conn.execute(sa.text("SELECT name FROM permissions"))]

    # Filter for new permissions not already in the database
    new_permissions_to_insert = [
        {'name': perm.value} for perm in PermissionEnum 
        if perm.value not in existing_permissions
    ]

    if new_permissions_to_insert:
        op.bulk_insert(permissions_table, new_permissions_to_insert)

def downgrade() -> None:
    permissions_table = sa.table('permissions', sa.column('name', sa.String))

    # Get all permissions from the enum
    all_enum_permissions = [perm.value for perm in PermissionEnum]

    # Delete only the permissions that are defined in the enum
    op.execute(
        permissions_table.delete().where(permissions_table.c.name.in_(all_enum_permissions))
    )
