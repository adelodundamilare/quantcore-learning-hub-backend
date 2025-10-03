"""alter courselevelenum to uppercase

Revision ID: 1a5bb0803204
Revises: 8f8480b6c813
Create Date: 2025-10-03 08:04:17.472718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a5bb0803204'
down_revision: Union[str, None] = '8f8480b6c813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TYPE courselevelenum RENAME TO courselevelenum_old"))
    conn.execute(sa.text("CREATE TYPE courselevelenum AS ENUM ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'ALL')"))
    conn.execute(sa.text("""
        ALTER TABLE courses
        ALTER COLUMN level TYPE courselevelenum
        USING UPPER(level::text)::courselevelenum
    """))
    conn.execute(sa.text("DROP TYPE courselevelenum_old"))

def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TYPE courselevelenum RENAME TO courselevelenum_old"))
    conn.execute(sa.text("CREATE TYPE courselevelenum AS ENUM ('beginner', 'intermediate', 'advanced', 'all')"))
    conn.execute(sa.text("""
        ALTER TABLE courses
        ALTER COLUMN level TYPE courselevelenum
        USING LOWER(level::text)::courselevelenum
    """))
    conn.execute(sa.text("DROP TYPE courselevelenum_old"))