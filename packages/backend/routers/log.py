from crud.log import build_register, run_register
from db.connection import get_session
from fastapi import APIRouter, Depends
from schemas.event import EventInsertResponse
from schemas.log import BuildLogCreate, RunLogCreate
from sqlmodel import Session
from utils.cache import invalidate_log_cache

router = APIRouter(tags=["Log"])


@router.post("/api/v2/events/build", response_model=EventInsertResponse)
def register_build_log(event: BuildLogCreate, db: Session = Depends(get_session)):
    inserted = build_register(db, event.model_dump())
    if inserted:
        invalidate_log_cache("build", event.class_div, event.hw_name, event.student_key)
    return EventInsertResponse(inserted=inserted)


@router.post("/api/v2/events/run", response_model=EventInsertResponse)
def register_run_log(event: RunLogCreate, db: Session = Depends(get_session)):
    inserted = run_register(db, event.model_dump())
    if inserted:
        invalidate_log_cache("run", event.class_div, event.hw_name, event.student_key)
    return EventInsertResponse(inserted=inserted)
