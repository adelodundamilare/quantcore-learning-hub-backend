"""add_soft_delete_and_audit_fields_to_user_school_association

Revision ID: eaa0409251f0
Revises: b8f2e0898753
Create Date: 2025-11-07 22:28:23.397411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'eaa0409251f0'
down_revision: Union[str, None] = 'b8f2e0898753'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete and audit fields to user_school_association table
    op.add_column('user_school_association', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_school_association', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('user_school_association', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove soft delete and audit fields from user_school_association table
    op.drop_column('user_school_association', 'updated_at')
    op.drop_column('user_school_association', 'created_at')
    op.drop_column('user_school_association', 'deleted_at')
