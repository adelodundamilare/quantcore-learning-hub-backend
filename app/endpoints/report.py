from typing import Optional
from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.schemas.report import AdminDashboardReportSchema, AdminDashboardStatsSchema, LeaderboardResponseSchema, SchoolDashboardStatsSchema, SchoolReportSchema, TradingLeaderboardResponseSchema
from app.services.report import report_service

router = APIRouter()

@router.get("/schools/{school_id}/report", response_model=APIResponse[SchoolReportSchema])
def get_school_report(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    report_data = report_service.get_school_report(db, school_id=school_id, current_user_context=context, start_date=start_date, end_date=end_date)
    return APIResponse(message="School report retrieved successfully", data=report_data)


@router.get("/schools/{school_id}/leaderboard", response_model=APIResponse[LeaderboardResponseSchema])
async def get_school_leaderboard(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    leaderboard_data = await report_service.get_school_leaderboard(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="School leaderboard retrieved successfully", data=leaderboard_data)


@router.get("/schools/{school_id}/trading-leaderboard", response_model=APIResponse[TradingLeaderboardResponseSchema])
async def get_school_trading_leaderboard(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    leaderboard_data = await report_service.get_trading_leaderboard(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="School trading leaderboard retrieved successfully", data=leaderboard_data)


@router.get("/schools/{school_id}/stats", response_model=APIResponse[SchoolDashboardStatsSchema])
def get_school_dashboard_stats(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    report_data = report_service.get_school_dashboard_stats(db, school_id=school_id, current_user_context=context, start_date=start_date, end_date=end_date)
    return APIResponse(message="School dashboard stats retrieved successfully", data=report_data)


@router.get("/admin/dashboard/report", response_model=APIResponse[AdminDashboardReportSchema])
def get_admin_dashboard_report(
    *,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    report_data = report_service.get_admin_dashboard_report(db, current_user_context=context, start_date=start_date, end_date=end_date)
    return APIResponse(message="Admin dashboard report retrieved successfully", data=report_data)


@router.get("/admin/dashboard/stats", response_model=APIResponse[AdminDashboardStatsSchema])
def get_admin_dashboard_stats(
    *,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    report_data = report_service.get_admin_dashboard_stats(db, current_user_context=context, start_date=start_date, end_date=end_date)
    return APIResponse(message="Admin dashboard stats retrieved successfully", data=report_data)
