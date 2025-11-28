"""add portfolio snapshots table

Revision ID: abc12345def
Revises: fd80e7d61a3e
Create Date: 2025-11-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'abc12345def'
down_revision: Union[str, None] = 'fd80e7d61a3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_portfolio_value', sa.Float(), nullable=False),
        sa.Column('cash_balance', sa.Float(), nullable=False),
        sa.Column('stocks_value', sa.Float(), nullable=False),
        sa.Column('holdings', sa.JSON(), nullable=False),
        sa.Column('realized_pnl', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('unrealized_pnl', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('total_pnl', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('percent_change', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('percent_change_from_start', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_portfolio_snapshots_user_id', 'portfolio_snapshots', ['user_id'], unique=False)
    op.create_index('ix_portfolio_snapshots_snapshot_date', 'portfolio_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_portfolio_snapshots_snapshot_date', table_name='portfolio_snapshots')
    op.drop_index('ix_portfolio_snapshots_user_id', table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
