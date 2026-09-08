from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

EVENT_MODELS = {"snapshot": Snapshot, "build": BuildLog, "run": RunLog}


def insert_event_once(db: Session, model, values: dict) -> bool:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        statement = (
            postgresql_insert(model)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(model.id)
        )
        inserted = db.exec(statement).first() is not None
        db.commit()
        return inserted

    try:
        db.add(model(**values))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def insert_event_batch(db: Session, events: list[tuple[str, dict]]) -> None:
    """Store a delivery batch atomically and accept already-seen event ids."""
    bind = db.get_bind()
    try:
        for event_type, values in events:
            model = EVENT_MODELS[event_type]
            if bind.dialect.name == "postgresql":
                db.exec(
                    postgresql_insert(model)
                    .values(**values)
                    .on_conflict_do_nothing(index_elements=["event_id"])
                )
            else:
                existing = db.exec(
                    select(model.id).where(model.event_id == values["event_id"])
                ).first()
                if existing is None:
                    db.add(model(**values))
        db.commit()
    except Exception:
        db.rollback()
        raise
