"""add_performance_indexes_for_critical_queries

Revision ID: 1aac137fe5a2
Revises: aa61e216e9ed
Create Date: 2025-11-15 21:13:04.479131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1aac137fe5a2'
down_revision: Union[str, None] = 'aa61e216e9ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_user_email_not_deleted', 'users', ['email'], unique=False, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index('idx_user_school_assoc', 'user_school_association', ['school_id', 'user_id', 'role_id'])
    op.create_index('idx_course_school_active', 'courses', ['school_id', 'is_active'], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index('idx_course_enrollment_user_course', 'course_enrollments', ['user_id', 'course_id'], unique=False, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index('idx_notifications_user_is_read', 'notifications', ['user_id', 'is_read'])
    op.create_index('idx_permissions_name', 'permissions', ['name'])
    op.create_index('idx_role_permissions_role', 'role_permissions', ['role_id'])
    op.create_index('idx_transactions_user_timestamp', 'transactions', ['user_id', 'created_at'])
    op.create_index('idx_course_rating_course_user', 'course_ratings', ['course_id', 'user_id'])


def downgrade() -> None:
    op.drop_index('idx_course_rating_course_user', table_name='course_ratings')
    op.drop_index('idx_transactions_user_timestamp', table_name='transactions')
    op.drop_index('idx_role_permissions_role', table_name='role_permissions')
    op.drop_index('idx_permissions_name', table_name='permissions')
    op.drop_index('idx_notifications_user_is_read', table_name='notifications')
    op.drop_index('idx_course_enrollment_user_course', table_name='course_enrollments')
    op.drop_index('idx_course_school_active', table_name='courses')
    op.drop_index('idx_user_school_assoc', table_name='user_school_association')
    op.drop_index('idx_user_email_not_deleted', table_name='users')