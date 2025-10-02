"""add reward rating

Revision ID: 8f8480b6c813
Revises: cba65ba3f5d2
Create Date: 2025-10-02 08:17:17.988340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f8480b6c813'
down_revision: Union[str, None] = 'cba65ba3f5d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('course_rewards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enrollment_id', sa.Integer(), nullable=False),
        sa.Column('reward_type', sa.String(length=50), nullable=False),
        sa.Column('reward_title', sa.String(length=255), nullable=False),
        sa.Column('reward_description', sa.Text(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('badge_url', sa.String(length=500), nullable=True),
        sa.Column('certificate_url', sa.String(length=500), nullable=True),
        sa.Column('awarded_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['enrollment_id'], ['course_enrollments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_rewards_id'), 'course_rewards', ['id'], unique=False)

    op.create_table('course_ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('review', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'course_id', name='unique_user_course_rating')
    )
    op.create_index(op.f('ix_course_ratings_id'), 'course_ratings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_course_ratings_id'), table_name='course_ratings')
    op.drop_table('course_ratings')
    op.drop_index(op.f('ix_course_rewards_id'), table_name='course_rewards')
    op.drop_table('course_rewards')