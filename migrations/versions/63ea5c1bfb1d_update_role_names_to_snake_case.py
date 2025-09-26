"""update role names to snake_case

Revision ID: 63ea5c1bfb1d
Revises: 3a2e13f12a38
Create Date: 2025-09-26 11:18:33.675613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63ea5c1bfb1d'
down_revision: Union[str, None] = '3a2e13f12a38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Define the mapping of old (camel case) to new (snake case) role names
    role_name_mapping = {
        "Super Admin": "super_admin",
        "School Admin": "school_admin",
        "Teacher": "teacher",
        "Student": "student",
        "Admin": "admin",
        "Member": "member",
    }

    # Update role names in the 'roles' table
    for old_name, new_name in role_name_mapping.items():
        op.execute(
            sa.text(f"UPDATE roles SET name = '{new_name}' WHERE name = '{old_name}'")
        )

def downgrade() -> None:
    # Define the reverse mapping of new (snake case) to old (camel case) role names
    role_name_reverse_mapping = {
        "super_admin": "Super Admin",
        "school_admin": "School Admin",
        "teacher": "Teacher",
        "student": "Student",
        "admin": "Admin",
        "member": "Member",
    }

    # Revert role names in the 'roles' table
    for new_name, old_name in role_name_reverse_mapping.items():
        op.execute(
            sa.text(f"UPDATE roles SET name = '{old_name}' WHERE name = '{new_name}'")
        )
