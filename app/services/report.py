from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.schemas.user import UserContext
from app.schemas.report import AdminDashboardReportSchema, MostActiveUserSchema, SchoolReportSchema, LeaderboardEntrySchema, LeaderboardResponseSchema, TopPerformerSchema
from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.course import course as crud_course
from app.crud.role import role as crud_role
from app.crud.school import school as crud_school
from app.utils.permission import PermissionHelper as permission_helper
from fastapi import HTTPException, status

class ReportService:
    def get_school_report(self, db: Session, school_id: int, current_user_context: UserContext, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> SchoolReportSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        total_courses_count = crud_course.get_courses_by_school_count(db, school_id=school_id, start_date=start_date, end_date=end_date)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        total_enrolled_students_count = crud_user.get_users_by_school_and_role_count(db, school_id=school_id, role_id=student_role.id, start_date=start_date, end_date=end_date)

        top_performer_data = crud_user.get_top_performer_by_exam_score(db, school_id=school_id, start_date=start_date, end_date=end_date)
        top_performer = TopPerformerSchema(**top_performer_data) if top_performer_data else None

        most_active_user_data = crud_user.get_most_active_user_by_lessons_completed(db, school_id=school_id, start_date=start_date, end_date=end_date)
        most_active_user = MostActiveUserSchema(**most_active_user_data._asdict()) if most_active_user_data else None

        return SchoolReportSchema(
            total_courses_count=total_courses_count,
            total_enrolled_students_count=total_enrolled_students_count,
            top_performer=top_performer,
            most_active_user=most_active_user
        )

    def get_school_leaderboard(
        self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> LeaderboardResponseSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        leaderboard_data = crud_user.get_leaderboard_data_for_school(db, school_id=school_id, skip=skip, limit=limit, start_date=start_date, end_date=end_date)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        total_students_in_school = crud_user.get_users_by_school_and_role_count(
            db, school_id=school_id, role_id=student_role.id, start_date=start_date, end_date=end_date
        )

        return LeaderboardResponseSchema(
            items=[LeaderboardEntrySchema(**entry._asdict()) for entry in leaderboard_data],
            total=total_students_in_school,
            skip=skip,
            limit=limit
        )

    def get_admin_dashboard_report(self, db: Session, current_user_context: UserContext, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> AdminDashboardReportSchema:
        # Permission check: Only Super Admin can access this report
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can access this report.")

        total_courses_count = crud_course.get_all_courses_count(db, start_date=start_date, end_date=end_date)
        total_schools_count = crud_school.get_all_schools_count(db, start_date=start_date, end_date=end_date)
        total_students_count = crud_user.get_all_students_count(db, start_date=start_date, end_date=end_date)

        return AdminDashboardReportSchema(
            total_courses_count=total_courses_count,
            total_schools_count=total_schools_count,
            total_students_count=total_students_count
        )

report_service = ReportService()
