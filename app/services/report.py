from sqlalchemy.orm import Session
from typing import List

from app.schemas.user import UserContext
from app.schemas.report import MostActiveUserSchema, SchoolReportSchema, LeaderboardEntrySchema, LeaderboardResponseSchema, TopPerformerSchema
from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.course import course as crud_course
from app.crud.role import role as crud_role
from app.utils.permission import PermissionHelper as permission_helper
from app.models.user import User
from fastapi import HTTPException, status

class ReportService:
    def get_school_report(self, db: Session, school_id: int, current_user_context: UserContext) -> SchoolReportSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        total_courses_count = crud_course.get_courses_by_school_count(db, school_id=school_id)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        total_enrolled_students_count = crud_user.get_users_by_school_and_role_count(db, school_id=school_id, role_id=student_role.id)

        top_performer_data = crud_user.get_top_performer_by_exam_score(db, school_id=school_id)
        top_performer = TopPerformerSchema(**top_performer_data._asdict()) if top_performer_data else None

        most_active_user_data = crud_user.get_most_active_user_by_lessons_completed(db, school_id=school_id)
        most_active_user = MostActiveUserSchema(**most_active_user_data._asdict()) if most_active_user_data else None

        return SchoolReportSchema(
            total_courses_count=total_courses_count,
            total_enrolled_students_count=total_enrolled_students_count,
            top_performer=top_performer,
            most_active_user=most_active_user
        )

    def get_school_leaderboard(
        self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100
    ) -> LeaderboardResponseSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        leaderboard_data = crud_user.get_leaderboard_data_for_school(db, school_id=school_id, skip=skip, limit=limit)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        total_students_in_school = crud_user.get_users_by_school_and_role_count(
            db, school_id=school_id, role_id=student_role.id
        )

        return LeaderboardResponseSchema(
            items=[LeaderboardEntrySchema(**entry._asdict()) for entry in leaderboard_data],
            total=total_students_in_school,
            skip=skip,
            limit=limit
        )

report_service = ReportService()
