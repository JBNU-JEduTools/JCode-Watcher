from sqlmodel import Session, select, func
from models.snapshot import Snapshot
from typing import List, Optional
from models.buildLog import BuildLog
from models.runLog import RunLog
from datetime import datetime

def get_monitoring_data(db: Session, class_div: str, hw_name: str):
    statement = (
        select(Snapshot)
        .where(Snapshot.class_div == class_div)
        .where(Snapshot.hw_name == hw_name)
    )
    results = db.exec(statement).all()
    return results

def get_graph_data(db: Session, class_div: str, hw_name: str, start: datetime, end: datetime):
    statement = (
        select(Snapshot.student_id, Snapshot.filename, Snapshot.file_size, Snapshot.timestamp)
        .where(Snapshot.class_div == class_div)
        .where(Snapshot.hw_name == hw_name)
        .where(Snapshot.timestamp >= start)
        .where(Snapshot.timestamp <= end)
        .order_by(Snapshot.student_id, Snapshot.filename, Snapshot.timestamp)
    )
    results = db.exec(statement).all()
    return results

def get_build_avg(db: Session, class_div: str, hw_name: str) -> Optional[float]:
    count_stmt = select(func.count(BuildLog.id)).where(
        BuildLog.class_div == class_div,
        BuildLog.hw_name == hw_name
    )
    count = db.exec(count_stmt).one() or 0

    student_stmt = select(func.count(func.distinct(BuildLog.student_id))).where(
        BuildLog.class_div == class_div,
        BuildLog.hw_name == hw_name
    )
    student = db.exec(student_stmt).one() or 0

    if student > 0:
        return round(count / student, 2)
    return 0.0

def get_run_avg(db: Session, class_div: str, hw_name: str) -> Optional[float]:
    count_stmt = select(func.count(RunLog.id)).where(
        RunLog.class_div == class_div,
        RunLog.hw_name == hw_name
    )
    count = db.exec(count_stmt).one() or 0

    student_stmt = select(func.count(func.distinct(RunLog.student_id))).where(
        RunLog.class_div == class_div,
        RunLog.hw_name == hw_name
    )
    student = db.exec(student_stmt).one() or 0

    if student > 0:
        return round(count / student, 2)
    return 0.0
    
    