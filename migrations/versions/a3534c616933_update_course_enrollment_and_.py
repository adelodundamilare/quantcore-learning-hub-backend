"""Update course enrollment and unenrollment logic

Revision ID: a3534c616933
Revises: b25b129c919f
Create Date: 2025-10-29 12:21:48.763792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a3534c616933'
down_revision: Union[str, None] = 'b25b129c919f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn)

    course_students_association = meta.tables['course_students_association']
    course_enrollments = meta.tables['course_enrollments']

    select_stmt = sa.select(
        course_students_association.c.user_id,
        course_students_association.c.course_id
    )
    existing_associations = conn.execute(select_stmt).fetchall()

    for user_id, course_id in existing_associations:
        enrollment_exists_stmt = sa.select(course_enrollments.c.id).where(
            sa.and_(
                course_enrollments.c.user_id == user_id,
                course_enrollments.c.course_id == course_id
            )
        )
        existing_enrollment = conn.execute(enrollment_exists_stmt).fetchone()

        if not existing_enrollment:
            insert_stmt = course_enrollments.insert().values(
                user_id=user_id,
                course_id=course_id,
                status='NOT_STARTED',
                progress_percentage=0,
                started_at=None,
                completed_at=None,
                created_at=sa.func.now(),
                updated_at=sa.func.now()
            )
            conn.execute(insert_stmt)

def downgrade() -> None:
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn)

    course_students_association = meta.tables['course_students_association']
    course_enrollments = meta.tables['course_enrollments']

    select_stmt = sa.select(
        course_students_association.c.user_id,
        course_students_association.c.course_id
    )
    existing_associations = conn.execute(select_stmt).fetchall()

    for user_id, course_id in existing_associations:
        delete_stmt = course_enrollments.delete().where(
            sa.and_(
                course_enrollments.c.user_id == user_id,
                course_enrollments.c.course_id == course_id
            )
        )
        conn.execute(delete_stmt)