
from models.snapshot import Snapshot
from sqlmodel import Session, select
from utils.assignment_key import assignment_predicates


def get_student_hw_files(
    db: Session, class_div: str, student_id: int, hw_name: str
) -> list[str]:
    statement = (
        select(Snapshot.relative_path)
        .distinct()
        .where(*assignment_predicates(Snapshot, class_div, hw_name))
        .where(Snapshot.student_key == str(student_id))
        .order_by(Snapshot.relative_path)
        .limit(1000)
    )
    return db.exec(statement).all()


def get_student_hw_timestamps(
    db: Session, class_div: str, student_id: int, hw_name: str, filename: str
) -> list[str]:
    statement = (
        select(Snapshot.occurred_at)
        .where(*assignment_predicates(Snapshot, class_div, hw_name))
        .where(Snapshot.student_key == str(student_id))
        .where(Snapshot.relative_path == filename)
    )

    results = db.exec(statement.order_by(Snapshot.occurred_at.desc()).limit(1000)).all()
    return [value.isoformat() for value in results]
