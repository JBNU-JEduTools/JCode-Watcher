from crud.dashboard import get_dashboard_summaries_by_assignment
from crud.event import insert_event_batch
from db.connection import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from schemas.batch import EventBatchRequest, EventBatchResponse
from schemas.log import BuildLogCreate, RunLogCreate
from schemas.snapshot import SnapshotCreate
from schemas.v2 import (
    DashboardV2Request,
    DashboardV2Response,
    DashboardV2Student,
    EventPage,
    EventPageItem,
    SnapshotPage,
    SnapshotPageItem,
)
from sqlmodel import Session, select
from utils.cache import invalidate_log_cache
from utils.cursor import encode_event_cursor, event_cursor_predicate

router = APIRouter(prefix="/api/v2", tags=["V2 queries"])


def event_page_statement(model, assignment_id: int, student_key: str, cursor=None):
    statement = select(model).where(
        model.assignment_id == assignment_id, model.student_key == student_key
    )
    if cursor is not None:
        statement = statement.where(event_cursor_predicate(model, cursor))
    return statement.order_by(model.occurred_at.desc(), model.id.desc())


@router.post(
    "/assignments/{assignment_id}/dashboard", response_model=DashboardV2Response
)
def dashboard(
    assignment_id: int, request: DashboardV2Request, db: Session = Depends(get_session)
):
    rows = get_dashboard_summaries_by_assignment(
        db, assignment_id, request.student_keys
    )
    return DashboardV2Response(
        students=[
            DashboardV2Student(**rows[key])
            for key in dict.fromkeys(request.student_keys)
        ]
    )


def _event_page(
    db: Session,
    model,
    assignment_id: int,
    student_key: str,
    limit: int,
    cursor: str | None,
):
    try:
        statement = event_page_statement(model, assignment_id, student_key, cursor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rows = db.exec(statement.limit(limit + 1)).all()
    page = rows[:limit]
    return EventPage(
        items=[EventPageItem.model_validate(row, from_attributes=True) for row in page],
        next_cursor=(
            encode_event_cursor(page[-1].occurred_at, page[-1].id)
            if len(rows) > limit and page
            else None
        ),
    )


@router.get(
    "/assignments/{assignment_id}/students/{student_key}/snapshots",
    response_model=SnapshotPage,
)
def snapshots(
    assignment_id: int,
    student_key: str,
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_session),
):
    try:
        statement = event_page_statement(Snapshot, assignment_id, student_key, cursor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rows = db.exec(statement.limit(limit + 1)).all()
    page = rows[:limit]
    return SnapshotPage(
        items=[
            SnapshotPageItem.model_validate(row, from_attributes=True) for row in page
        ],
        next_cursor=(
            encode_event_cursor(page[-1].occurred_at, page[-1].id)
            if len(rows) > limit and page
            else None
        ),
    )


@router.get(
    "/assignments/{assignment_id}/students/{student_key}/build",
    response_model=EventPage,
)
def build_events(
    assignment_id: int,
    student_key: str,
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_session),
):
    return _event_page(db, BuildLog, assignment_id, student_key, limit, cursor)


@router.get(
    "/assignments/{assignment_id}/students/{student_key}/run", response_model=EventPage
)
def run_events(
    assignment_id: int,
    student_key: str,
    limit: int = Query(default=200, ge=1, le=1000),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_session),
):
    return _event_page(db, RunLog, assignment_id, student_key, limit, cursor)


@router.post("/events/batch", response_model=EventBatchResponse)
def register_event_batch(
    request: EventBatchRequest, db: Session = Depends(get_session)
):
    schemas = {
        "snapshot": SnapshotCreate,
        "build": BuildLogCreate,
        "run": RunLogCreate,
    }
    parsed = []
    for item in request.events:
        try:
            event = schemas[item.type].model_validate(item.payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        parsed.append((item.type, event.model_dump()))

    insert_event_batch(db, parsed)
    for event_type, values in parsed:
        if event_type in {"build", "run"}:
            invalidate_log_cache(
                event_type,
                values["class_div"],
                values["hw_name"],
                values["student_key"],
            )
    return EventBatchResponse(
        acknowledged_event_ids=[values["event_id"] for _, values in parsed]
    )
