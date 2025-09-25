"""create token denylist table

Revision ID: 3a2e13f12a38
Revises: bc97769fe1dd
Create Date: 2025-09-25 20:48:21.034787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a2e13f12a38'
down_revision: Union[str, None] = 'bc97769fe1dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'token_denylist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(), nullable=False),
        sa.Column('exp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_token_denylist_id'), 'token_denylist', ['id'], unique=False)
    op.create_index(op.f('ix_token_denylist_jti'), 'token_denylist', ['jti'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_token_denylist_jti'), table_name='token_denylist')
    op.drop_index(op.f('ix_token_denylist_id'), table_name='token_denylist')
    op.drop_table('token_denylist')
