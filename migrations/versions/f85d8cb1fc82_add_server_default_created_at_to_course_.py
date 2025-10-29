"""add server default created at to course enrollment

Revision ID: f85d8cb1fc82
Revises: a3534c616933
Create Date: 2025-10-29 12:34:28.316848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f85d8cb1fc82'
down_revision: Union[str, None] = 'a3534c616933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('course_enrollments', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('course_enrollments', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               server_default=sa.func.now(),
               onupdate=sa.func.now(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('course_enrollments', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               onupdate=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('course_enrollments', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               server_default=None,
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
