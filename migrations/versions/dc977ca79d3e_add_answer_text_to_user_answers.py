"""add answer_text to user_answers

Revision ID: <new_revision_id>
Revises: 1dbf19470233
Create Date: <timestamp>
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '<new_revision_id>'
down_revision: Union[str, None] = '1dbf19470233'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_answers', sa.Column('answer_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_answers', 'answer_text')