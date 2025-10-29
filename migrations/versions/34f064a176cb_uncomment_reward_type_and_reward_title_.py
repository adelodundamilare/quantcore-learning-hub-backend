"""Uncomment reward_type and reward_title in CourseReward model

Revision ID: 34f064a176cb
Revises: 4579544f5010
Create Date: 2025-10-29 12:44:43.061483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '34f064a176cb'
down_revision: Union[str, None] = '4579544f5010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('course_rewards')]

    if 'reward_type' not in columns:
        op.add_column('course_rewards', sa.Column('reward_type', sa.String(length=50), nullable=False))

    if 'reward_title' not in columns:
        op.add_column('course_rewards', sa.Column('reward_title', sa.String(length=255), nullable=False))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('course_rewards')]

    if 'reward_title' in columns:
        op.drop_column('course_rewards', 'reward_title')

    if 'reward_type' in columns:
        op.drop_column('course_rewards', 'reward_type')