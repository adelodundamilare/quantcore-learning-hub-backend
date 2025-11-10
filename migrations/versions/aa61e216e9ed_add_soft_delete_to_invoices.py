"""add_soft_delete_to_invoices

Revision ID: aa61e216e9ed
Revises: eaa0409251f0
Create Date: 2025-11-10 08:18:08.153655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'aa61e216e9ed'
down_revision: Union[str, None] = 'eaa0409251f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete column to invoices table
    op.add_column('invoices', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # Remove soft delete column from invoices table
    op.drop_column('invoices', 'deleted_at')
    # ### end Alembic commands ###
