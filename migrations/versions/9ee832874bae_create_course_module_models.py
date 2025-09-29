"""create course module models

Revision ID: 9ee832874bae
Revises: 63ea5c1bfb1d
Create Date: 2025-09-28 21:58:38.838213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '9ee832874bae'
down_revision: Union[str, None] = '63ea5c1bfb1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'courselevelenum'"))
    if not result.fetchone():
        conn.execute(sa.text("CREATE TYPE courselevelenum AS ENUM ('beginner', 'intermediate', 'advanced', 'all')"))

    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('thumbnail', sa.String(), nullable=True),
        sa.Column('level', postgresql.ENUM('beginner', 'intermediate', 'advanced', 'all', name='courselevelenum', create_type=False), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_title'), 'courses', ['title'], unique=False)
    op.create_index('ix_courses_school_id', 'courses', ['school_id'])
    op.create_index('ix_courses_level', 'courses', ['level'])
    op.create_index('ix_courses_is_active', 'courses', ['is_active'])
    op.create_index('ix_courses_active_not_deleted', 'courses', ['is_active'],
                   postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('course_students_association',
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('course_id', 'user_id')
    )
    op.create_index('ix_course_students_course_id', 'course_students_association', ['course_id'])
    op.create_index('ix_course_students_user_id', 'course_students_association', ['user_id'])
    op.create_table('course_teachers_association',
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('course_id', 'user_id')
    )
    op.create_index('ix_course_teachers_course_id', 'course_teachers_association', ['course_id'])
    op.create_index('ix_course_teachers_user_id', 'course_teachers_association', ['user_id'])

def downgrade() -> None:
    op.drop_index('ix_course_teachers_user_id', table_name='course_teachers_association')
    op.drop_index('ix_course_teachers_course_id', table_name='course_teachers_association')
    op.drop_table('course_teachers_association')
    op.drop_index('ix_course_students_user_id', table_name='course_students_association')
    op.drop_index('ix_course_students_course_id', table_name='course_students_association')
    op.drop_table('course_students_association')
    op.drop_index('ix_courses_active_not_deleted', table_name='courses')
    op.drop_index('ix_courses_is_active', table_name='courses')
    op.drop_index('ix_courses_level', table_name='courses')
    op.drop_index('ix_courses_school_id', table_name='courses')
    op.drop_index(op.f('ix_courses_title'), table_name='courses')
    op.drop_index(op.f('ix_courses_id'), table_name='courses')
    op.drop_table('courses')
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name IN ('courses', 'course_students_association', 'course_teachers_association')"))
    if not result.fetchone():
        conn.execute(sa.text("DROP TYPE IF EXISTS courselevelenum"))