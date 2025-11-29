"""initial

Revision ID: a96c89bda0b2
Revises: 86a35f320e35
Create Date: 2025-11-29 14:00:29.199702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a96c89bda0b2'
down_revision: Union[str, None] = '86a35f320e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
