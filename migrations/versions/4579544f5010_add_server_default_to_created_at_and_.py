"""Add server_default to created_at and updated_at for lesson_progress, course_ratings, and course_rewards

Revision ID: 4579544f5010
Revises: f85d8cb1fc82
Create Date: 2025-10-29 12:40:52.775813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4579544f5010'
down_revision: Union[str, None] = 'f85d8cb1fc82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('course_rewards', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('course_rewards', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               onupdate=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('lesson_progress', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('lesson_progress', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               onupdate=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    # For course_ratings, the autogenerate might have dropped it, so we need to add it back if it's missing
    # or just alter if it exists. Assuming it exists and just needs alteration.
    op.alter_column('course_ratings', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('course_ratings', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               onupdate=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('lesson_progress', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               onupdate=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('lesson_progress', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('course_rewards', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               onupdate=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('course_rewards', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('course_ratings', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               onupdate=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('course_ratings', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
