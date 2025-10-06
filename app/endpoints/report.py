from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.schemas.report import SchoolReportSchema
from app.services.report import report_service

router = APIRouter()

@router.get("/schools/{school_id}/report", response_model=APIResponse[SchoolReportSchema])
def get_school_report(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    report_data = report_service.get_school_report(db, school_id=school_id, current_user_context=context)
    return APIResponse(message="School report retrieved successfully", data=report_data)
