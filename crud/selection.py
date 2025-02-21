from typing import List
from sqlmodel import Session, select
from app.models.snapshot import Snapshot

def get_student_hw_files(db: Session, class_div: str, student_id: int, hw_name: str) -> List[Snapshot]:
    statement = (
        select(Snapshot)
        .where(Snapshot.class_div == class_div)
        .where(Snapshot.student_id == student_id)
        .where(Snapshot.hw_name == hw_name)
    )
    
    return db.exec(statement).all()

def get_student_hw_timestamps(db: Session, class_div: str, student_id: int, hw_name: str, filename: str) -> List[str]:
    statement = (
        select(Snapshot.timestamp)
        .where(Snapshot.class_div == class_div)
        .where(Snapshot.student_id == student_id)
        .where(Snapshot.hw_name == hw_name)
        .where(Snapshot.filename == filename)
    )
    
    results = db.exec(statement).all()
    return results