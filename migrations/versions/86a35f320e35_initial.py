"""initial

Revision ID: 86a35f320e35
Revises:
Create Date: 2025-11-29 13:58:33.338888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '86a35f320e35'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass