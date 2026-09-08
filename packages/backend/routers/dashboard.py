from fastapi import APIRouter, Depends
from sqlmodel import Session

from crud.dashboard import get_dashboard_summaries
from db.connection import get_session
from schemas.student import DashboardStudentSummary, DashboardSummaryRequest, DashboardSummaryResponse


router = APIRouter(tags=["Dashboard"])


@router.post("/api/dashboard/{class_div}/{hw_name}/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    class_div: str,
    hw_name: str,
    request: DashboardSummaryRequest,
    db: Session = Depends(get_session),
):
    summaries = get_dashboard_summaries(db, class_div, hw_name, request.student_ids)
    return DashboardSummaryResponse(
        students=[DashboardStudentSummary(**summaries[student_id]) for student_id in dict.fromkeys(request.student_ids)]
    )
