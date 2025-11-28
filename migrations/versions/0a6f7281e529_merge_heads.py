"""merge heads

Revision ID: 0a6f7281e529
Revises: 1aac137fe5a2, abc12345def
Create Date: 2025-11-28 16:13:52.791868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a6f7281e529'
down_revision: Union[str, None] = ('1aac137fe5a2', 'abc12345def')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
