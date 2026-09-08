from datetime import datetime

from db.connection import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from schemas.student import (
    BuildLogResponse,
    GraphResponse,
    MonitoringResponse,
    RunLogResponse,
    SnapshotAvgResponse,
)
from services.student import (
    calculate_assignment_snapshot_avg,
    calculate_snapshot_avg,
    fetch_build_log,
    fetch_run_log,
    graph_data_by_minutes,
)
from sqlmodel import Session

# 학생별
router = APIRouter(tags=["Student"])


# 학생별, 코드별 평균 스냅샷 개수, 크기 계산
@router.get(
    "/api/snapshot_avg/{class_div}/{hw_name}/{student_id}/{filename}",
    response_model=SnapshotAvgResponse,
)
def get_snapshot_avg(
    class_div: str,
    hw_name: str,
    student_id: int,
    filename: str,
    db: Session = Depends(get_session),
):

    results = calculate_snapshot_avg(db, class_div, hw_name, student_id, filename)

    if not results:
        return SnapshotAvgResponse(snapshot_avg=None, snapshot_size_avg=None)

    return results


# 학생별, 과제별 평균 스냅샷 개수, 크기 계산
@router.get(
    "/api/assignments/snapshot_avg/{class_div}/{hw_name}/{student_id}",
    response_model=MonitoringResponse,
)
def get_assignment_snapshot_avg(
    class_div: str, student_id: int, hw_name: str, db: Session = Depends(get_session)
):
    result = calculate_assignment_snapshot_avg(db, class_div, student_id, hw_name)

    if not result:
        return MonitoringResponse(
            snapshot_avg=None,
            snapshot_size_avg=None,
            first=None,
            last=None,
            total=None,
            interval=None,
        )

    return result


# 학생별 그래프 데이터 조회 - 시간별 스냅샷 크기 변화
@router.get(
    "/api/graph_data/{class_div}/{hw_name}/{student_id}/{interval}",
    response_model=GraphResponse,
)
async def get_graph_data_by_minutes(
    class_div: str,
    hw_name: str,
    student_id: int,
    interval: int,
    db: Session = Depends(get_session),
):
    result = await graph_data_by_minutes(db, class_div, hw_name, student_id, interval)

    if not result:
        return {"trends": []}

    return result


# 빌드 로그 조회
@router.get(
    "/api/{class_div}/{hw_name}/{student_id}/logs/build",
    response_model=list[BuildLogResponse],
)
def get_build_log(
    class_div: str,
    hw_name: str,
    student_id: int,
    response: Response,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_session),
):
    try:
        items, next_cursor = fetch_build_log(
            db, class_div, hw_name, student_id, from_time, to_time, limit, cursor
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if next_cursor is not None:
        response.headers["X-Next-Cursor"] = str(next_cursor)
    return items


# 실행 로그 조회
@router.get(
    "/api/{class_div}/{hw_name}/{student_id}/logs/run",
    response_model=list[RunLogResponse],
)
def get_run_log(
    class_div: str,
    hw_name: str,
    student_id: int,
    response: Response,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_session),
):
    try:
        items, next_cursor = fetch_run_log(
            db, class_div, hw_name, student_id, from_time, to_time, limit, cursor
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if next_cursor is not None:
        response.headers["X-Next-Cursor"] = str(next_cursor)
    return items
