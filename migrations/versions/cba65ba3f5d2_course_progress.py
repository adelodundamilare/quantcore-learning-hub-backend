"""course progress

Revision ID: cba65ba3f5d2
Revises: <new_revision_id>
Create Date: 2025-10-02 07:39:29.871497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cba65ba3f5d2'
down_revision: Union[str, None] = '<new_revision_id>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('course_enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'DROPPED', name='enrollmentstatusenum'), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('progress_percentage', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_enrollments_id'), 'course_enrollments', ['id'], unique=False)

    op.create_table('lesson_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enrollment_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['enrollment_id'], ['course_enrollments.id'], ),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lesson_progress_id'), 'lesson_progress', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_lesson_progress_id'), table_name='lesson_progress')
    op.drop_table('lesson_progress')
    op.drop_index(op.f('ix_course_enrollments_id'), table_name='course_enrollments')
    op.drop_table('course_enrollments')
