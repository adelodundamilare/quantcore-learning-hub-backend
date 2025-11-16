from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.schemas.user import UserContext
from app.schemas.report import SchoolReportSchema, StudentExamStats
from app.schemas.report import (
    AdminDashboardReportSchema, AdminDashboardStatsSchema, MostActiveUserSchema,
    SchoolDashboardStatsSchema, SchoolReportSchema, LeaderboardEntrySchema,
    LeaderboardResponseSchema, TopPerformerSchema, TradingLeaderboardEntrySchema,
    TradingLeaderboardResponseSchema
)
from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.course import course as crud_course
from app.crud.role import role as crud_role
from app.crud.school import school as crud_school
from app.crud.exam import exam as crud_exam
from app.crud.exam_attempt import exam_attempt as crud_exam_attempt
from app.services.exam import exam_service
from app.services.trading import trading_service
from app.services.stripe import stripe_service
from app.schemas.report import StudentExamStats
from app.crud.report import trading_leaderboard_snapshot, leaderboard_snapshot
from app.utils.permission import PermissionHelper as permission_helper
from app.utils.events import event_bus
from fastapi import HTTPException, status
from app.core.database import SessionLocal
import asyncio

class ReportService:
    def get_student_exam_stats(self, db: Session, current_user_context: UserContext) -> StudentExamStats:
        if not permission_helper.is_student(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This report is only for students.")

        user_id = current_user_context.user.id
        course_ids, curriculum_ids = exam_service._get_user_course_and_curriculum_ids(db, current_user_context)

        if not course_ids and not curriculum_ids:
            return StudentExamStats(pending_exams=0, overall_grade_percentage=0.0)

        all_student_exams = crud_exam.get_multi_filtered(
            db, course_ids=course_ids, curriculum_ids=curriculum_ids
        )

        completed_exam_ids = crud_exam_attempt.get_user_completed_exam_ids(db, user_id=user_id)
        pending_exams_count = len([exam for exam in all_student_exams if exam.id not in completed_exam_ids])
        overall_grade_percentage = crud_exam_attempt.get_user_average_score(db, user_id=user_id)

        return StudentExamStats(
            pending_exams=pending_exams_count,
            overall_grade_percentage=overall_grade_percentage
        )

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

    async def get_school_leaderboard(
        self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100
    ) -> LeaderboardResponseSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        snapshots = leaderboard_snapshot.get_all_snapshots_for_school(db, school_id=school_id, skip=skip, limit=limit)
        total_snapshots = leaderboard_snapshot.count_snapshots_for_school(db, school_id=school_id)

        leaderboard_entries = []
        for snapshot in snapshots:
            leaderboard_entries.append(LeaderboardEntrySchema(
                student_id=snapshot.student_id,
                student_full_name=snapshot.student_full_name,
                student_email=snapshot.student_email,
                lessons_completed=snapshot.lessons_completed,
                accumulated_exam_score=snapshot.accumulated_exam_score,
                total_rewards=snapshot.total_rewards
            ))

        return LeaderboardResponseSchema(
            items=leaderboard_entries,
            total=total_snapshots,
            skip=skip,
            limit=limit
        )

    async def precompute_leaderboard(self, db: Session, school_id: int):
        try:
            student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
            if not student_role:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

            students = crud_user.get_users_by_school_and_role(db, school_id=school_id, role_id=student_role.id)
            leaderboard_data = crud_user.get_leaderboard_data_for_school(db, school_id=school_id, skip=0, limit=len(students))
            leaderboard_snapshot.delete_all_snapshots_for_school(db, school_id=school_id)

            new_snapshots = []
            for entry in leaderboard_data:
                snapshot_data = {
                    "student_id": entry.student_id,
                    "student_full_name": entry.student_full_name,
                    "student_email": entry.student_email,
                    "lessons_completed": entry.lessons_completed,
                    "accumulated_exam_score": entry.accumulated_exam_score,
                    "total_rewards": entry.total_rewards,
                    "timestamp": datetime.utcnow(),
                    "school_id": school_id
                }
                new_snapshots.append(snapshot_data)

            leaderboard_snapshot.bulk_create_leaderboard_snapshots(db, snapshots_data=new_snapshots)
        except Exception as e:
            print(f"Error precomputing leaderboard for school {school_id}: {e}")
            raise

    async def precompute_trading_leaderboard(
        self, db: Session, school_id: int, current_user_context: UserContext
    ):
        try:
            student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
            if not student_role:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

            students = crud_user.get_users_by_school_and_role(db, school_id=school_id, role_id=student_role.id)

            tasks = []
            for student in students:
                tasks.append(trading_service.get_trading_account_summary(db, user_id=student.id))

            summaries = await asyncio.gather(*tasks, return_exceptions=True)
            trading_leaderboard_snapshot.delete_all_snapshots_for_school(db, school_id=school_id)

            new_snapshots = []
            for i, student in enumerate(students):
                summary = summaries[i]
                if isinstance(summary, Exception):
                    print(f"Error fetching trading summary for student {student.id}: {summary}")
                    continue

                snapshot_data = {
                    "student_id": student.id,
                    "student_full_name": student.full_name,
                    "student_email": student.email,
                    "starting_capital": summary.starting_capital,
                    "current_balance": summary.current_balance,
                    "trading_profit": summary.trading_profit,
                    "timestamp": datetime.utcnow(),
                    "school_id": school_id
                }
                new_snapshots.append(snapshot_data)

            trading_leaderboard_snapshot.bulk_create_trading_leaderboard_snapshots(db, snapshots_data=new_snapshots)
        except Exception as e:
            print(f"Error precomputing trading leaderboard for school {school_id}: {e}")
            raise

    async def get_trading_leaderboard(
        self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100
    ) -> TradingLeaderboardResponseSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)

        snapshots = trading_leaderboard_snapshot.get_all_snapshots_for_school(db, school_id=school_id, skip=skip, limit=limit)
        total_snapshots = trading_leaderboard_snapshot.count_snapshots_for_school(db, school_id=school_id)

        leaderboard_entries = []
        for snapshot in snapshots:
            leaderboard_entries.append(TradingLeaderboardEntrySchema(
                student_id=snapshot.student_id,
                student_full_name=snapshot.student_full_name,
                student_email=snapshot.student_email,
                starting_capital=snapshot.starting_capital,
                current_balance=snapshot.current_balance,
                trading_profit=snapshot.trading_profit
            ))

        return TradingLeaderboardResponseSchema(
            items=leaderboard_entries,
            total=total_snapshots,
            skip=skip,
            limit=limit
        )

    def get_school_dashboard_stats(self, db: Session, school_id: int, current_user_context: UserContext, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> SchoolReportSchema:
        permission_helper.require_school_view_permission(current_user_context, school_id)
        permission_helper.require_not_student(current_user_context)

        total_courses_count = crud_course.get_courses_by_school_count(db, school_id=school_id, start_date=start_date, end_date=end_date)

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        total_students_count = crud_user.get_users_by_school_and_role_count(db, school_id=school_id, role_id=student_role.id, start_date=start_date, end_date=end_date)

        total_teams_count = crud_user.get_non_student_users_by_school_count(db, school_id=school_id, start_date=start_date, end_date=end_date)

        return SchoolDashboardStatsSchema(
            total_students=total_students_count,
            total_courses=total_courses_count,
            total_teams=total_teams_count
        )

    async def get_admin_dashboard_report(self, db: Session, current_user_context: UserContext, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> AdminDashboardReportSchema:
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can access this report.")

        total_courses_count = crud_course.get_all_courses_count(db, start_date=start_date, end_date=end_date)
        total_schools_count = crud_school.get_all_schools_count(db, start_date=start_date, end_date=end_date)
        total_students_count = crud_user.get_all_students_count(db, start_date=start_date, end_date=end_date)
        total_revenue = await stripe_service.get_total_revenue(start_date=start_date, end_date=end_date)

        return AdminDashboardReportSchema(
            total_courses_count=total_courses_count,
            total_schools_count=total_schools_count,
            total_students_count=total_students_count,
            total_revenue=total_revenue
        )

    def get_admin_dashboard_stats(self, db: Session, current_user_context: UserContext, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> AdminDashboardReportSchema:
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can access this report.")

        total_courses_count = crud_course.get_all_courses_count(db, start_date=start_date, end_date=end_date)
        total_students_count = crud_user.get_all_students_count(db, start_date=start_date, end_date=end_date)
        total_teachers_count = crud_user.get_all_teachers_count(db, start_date=start_date, end_date=end_date)

        return AdminDashboardStatsSchema(
            total_courses=total_courses_count,
            total_students=total_students_count,
            total_teachers=total_teachers_count
        )

    async def update_student_leaderboard(self, db: Session, student_id: int, school_id: int):
        try:
            student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
            if not student_role:
                return

            association = crud_user.get_association_by_user_school_role(
                db, user_id=student_id, school_id=school_id, role_id=student_role.id
            )
            if not association:
                return

            student = crud_user.get(db, id=student_id)
            if not student:
                return

            leaderboard_data = crud_user.get_leaderboard_data_for_student(
                db, school_id=school_id, student_id=student_id
            )

            if not leaderboard_data:
                return

            snapshot_data = {
                "student_id": student_id,
                "student_full_name": leaderboard_data.student_full_name,
                "student_email": leaderboard_data.student_email,
                "lessons_completed": leaderboard_data.lessons_completed,
                "accumulated_exam_score": leaderboard_data.accumulated_exam_score,
                "total_rewards": leaderboard_data.total_rewards,
                "school_id": school_id,
                "timestamp": datetime.utcnow()
            }

            leaderboard_snapshot.update_or_create_snapshot(db, student_id, school_id, snapshot_data)
        except Exception as e:
            print(f"Error updating student leaderboard for student {student_id}: {e}")

    async def update_student_trading_leaderboard(self, db: Session, student_id: int, school_id: int):
        try:
            student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
            if not student_role:
                return

            association = crud_user.get_association_by_user_school_role(
                db, user_id=student_id, school_id=school_id, role_id=student_role.id
            )
            if not association:
                return

            student = crud_user.get(db, id=student_id)
            if not student:
                return

            trading_summary = await trading_service.get_trading_account_summary(db, user_id=student_id)

            snapshot_data = {
                "student_id": student_id,
                "student_full_name": student.full_name,
                "student_email": student.email,
                "starting_capital": trading_summary.starting_capital,
                "current_balance": trading_summary.current_balance,
                "trading_profit": trading_summary.trading_profit,
                "school_id": school_id,
                "timestamp": datetime.utcnow()
            }

            trading_leaderboard_snapshot.update_or_create_snapshot(db, student_id, school_id, snapshot_data)
        except Exception as e:
            print(f"Error updating student trading leaderboard for student {student_id}: {e}")


async def handle_course_completion_event(data: dict):
    student_id = data.get("student_id")
    course_id = data.get("course_id")
    school_id = data.get("school_id")
    if not all([student_id, course_id, school_id]):
        return

    db = SessionLocal()
    try:
        await report_service.update_student_leaderboard(db, student_id, school_id)
    finally:
        db.close()


async def handle_reward_awarded_event(data: dict):
    student_id = data.get("student_id")
    school_id = data.get("school_id")
    if not all([student_id, school_id]):
        return

    db = SessionLocal()
    try:
        await report_service.update_student_leaderboard(db, student_id, school_id)
    finally:
        db.close()


async def handle_trade_executed_event(data: dict):
    student_id = data.get("student_id")
    if not student_id:
        return

    db = SessionLocal()
    try:
        associations = crud_user.get_student_school_associations(db, student_id)
        for association in associations:
            await report_service.update_student_trading_leaderboard(db, student_id, association.school_id)
    finally:
        db.close()


report_service = ReportService()

event_bus.subscribe("course_completed", handle_course_completion_event)
event_bus.subscribe("reward_awarded", handle_reward_awarded_event)
event_bus.subscribe("trade_executed", handle_trade_executed_event)