"""insert new permissions

Revision ID: aca92d4f646a
Revises: 9eb517682281
Create Date: 2025-09-25 15:36:28.806593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aca92d4f646a'
down_revision: Union[str, None] = '9eb517682281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
