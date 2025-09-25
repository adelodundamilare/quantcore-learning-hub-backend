"""seed roles and permissions

Revision ID: 41cf89393b31
Revises: 7b9a436f87f8
Create Date: 2025-09-25 12:21:44.174147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from app.core.constants import RoleEnum, PermissionEnum


# revision identifiers, used by Alembic.
revision: str = '41cf89393b31'
down_revision: Union[str, None] = '7b9a436f87f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define table structures for the migration
    roles_table = table('roles',
        column('name', sa.String)
    )

    permissions_table = table('permissions',
        column('name', sa.String)
    )

    # Insert roles
    op.bulk_insert(roles_table,
        [{'name': role.value} for role in RoleEnum]
    )

    # Insert permissions
    op.bulk_insert(permissions_table,
        [{'name': perm.value} for perm in PermissionEnum]
    )


def downgrade() -> None:
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM roles")