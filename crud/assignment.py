from sqlmodel import Session, select
from app.models.snapshot import Snapshot

def get_monitoring_data(db: Session, class_div: str, hw_name: str):
    statement = (
        select(Snapshot)
        .where(Snapshot.class_div == class_div)
        .where(Snapshot.hw_name == hw_name)
    )
    results = db.exec(statement).all()
    return results
