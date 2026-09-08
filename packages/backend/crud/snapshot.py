from crud.event import insert_event_once
from models.snapshot import Snapshot
from sqlmodel import Session


def snapshot_register(db: Session, snapshot_data: dict) -> bool:
    return insert_event_once(db, Snapshot, snapshot_data)
