from crud.snapshot import snapshot_register
from db.connection import get_session
from fastapi import APIRouter, Depends
from schemas.event import EventInsertResponse
from schemas.snapshot import SnapshotCreate
from sqlmodel import Session

router = APIRouter(tags=["Snapshot"])


@router.post("/api/v2/events/snapshot", response_model=EventInsertResponse)
def register_snapshot(event: SnapshotCreate, db: Session = Depends(get_session)):
    return EventInsertResponse(inserted=snapshot_register(db, event.model_dump()))
