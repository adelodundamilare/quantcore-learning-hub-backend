"""Add exam, question, user answer, and exam attempt modules, and simplify question answers

Revision ID: 1dbf19470233
Revises: b8998c14dfd4
Create Date: 2025-09-30 12:05:58.451231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1dbf19470233'
down_revision: Union[str, None] = 'b8998c14dfd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'examattemptstatusenum'"))
    if not result.fetchone():
        conn.execute(sa.text("CREATE TYPE examattemptstatusenum AS ENUM ('IN_PROGRESS', 'COMPLETED', 'GRADED')"))

    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'questiontypeenum'"))
    if not result.fetchone():
        conn.execute(sa.text("CREATE TYPE questiontypeenum AS ENUM ('MULTIPLE_CHOICE', 'TRUE_FALSE')"))

    op.create_table('exams',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('course_id', sa.Integer(), nullable=True),
    sa.Column('curriculum_id', sa.Integer(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('pass_percentage', sa.Float(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('allow_multiple_attempts', sa.Boolean(), nullable=False),
    sa.Column('show_results_immediately', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['curriculum_id'], ['curriculums.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exams_id'), 'exams', ['id'], unique=False)
    op.create_index(op.f('ix_exams_title'), 'exams', ['title'], unique=False)

    op.create_table('exam_attempts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('exam_id', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('passed', sa.Boolean(), nullable=True),
    sa.Column('status', postgresql.ENUM('IN_PROGRESS', 'COMPLETED', 'GRADED', name='examattemptstatusenum', create_type=False), nullable=False, server_default='IN_PROGRESS'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_attempts_id'), 'exam_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_exam_attempts_user_id'), 'exam_attempts', ['user_id'], unique=False)
    op.create_index(op.f('ix_exam_attempts_exam_id'), 'exam_attempts', ['exam_id'], unique=False)

    op.create_table('questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('exam_id', sa.Integer(), nullable=False),
    sa.Column('question_text', sa.String(), nullable=False),
    sa.Column('question_type', postgresql.ENUM('MULTIPLE_CHOICE', 'TRUE_FALSE', name='questiontypeenum', create_type=False), nullable=False),
    sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('correct_answer', sa.Integer(), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    op.create_index(op.f('ix_questions_exam_id'), 'questions', ['exam_id'], unique=False)

    op.create_table('user_answers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('exam_attempt_id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('selected_option', sa.Integer(), nullable=True),
    sa.Column('is_correct', sa.Boolean(), nullable=True),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['exam_attempt_id'], ['exam_attempts.id'], ),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_answers_id'), 'user_answers', ['id'], unique=False)
    op.create_index(op.f('ix_user_answers_exam_attempt_id'), 'user_answers', ['exam_attempt_id'], unique=False)
    op.create_index(op.f('ix_user_answers_question_id'), 'user_answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_user_answers_user_id'), 'user_answers', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_answers_user_id'), table_name='user_answers')
    op.drop_index(op.f('ix_user_answers_question_id'), table_name='user_answers')
    op.drop_index(op.f('ix_user_answers_exam_attempt_id'), table_name='user_answers')
    op.drop_index(op.f('ix_user_answers_id'), table_name='user_answers')
    op.drop_table('user_answers')

    op.drop_index(op.f('ix_questions_exam_id'), table_name='questions')
    op.drop_index(op.f('ix_questions_id'), table_name='questions')
    op.drop_table('questions')

    op.drop_index(op.f('ix_exam_attempts_exam_id'), table_name='exam_attempts')
    op.drop_index(op.f('ix_exam_attempts_user_id'), table_name='exam_attempts')
    op.drop_index(op.f('ix_exam_attempts_id'), table_name='exam_attempts')
    op.drop_table('exam_attempts')

    op.drop_index(op.f('ix_exams_title'), table_name='exams')
    op.drop_index(op.f('ix_exams_id'), table_name='exams')
    op.drop_table('exams')

    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name IN ('exams', 'exam_attempts', 'questions', 'user_answers')"))
    if not result.fetchone():
        conn.execute(sa.text("DROP TYPE IF EXISTS questiontypeenum"))
        conn.execute(sa.text("DROP TYPE IF EXISTS examattemptstatusenum"))