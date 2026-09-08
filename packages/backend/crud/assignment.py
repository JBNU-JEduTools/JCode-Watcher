from datetime import datetime

from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from sqlalchemy import func
from sqlmodel import Session, select
from utils.assignment_key import assignment_predicates


def get_monitoring_summary(db: Session, class_div: str, hw_name: str):
    filters = assignment_predicates(Snapshot, class_div, hw_name)
    distribution = db.exec(
        select(
            func.percentile_cont(0.9).within_group(Snapshot.file_size),
            func.percentile_cont(0.5).within_group(Snapshot.file_size),
        ).where(*filters)
    ).one()
    per_student = (
        select(
            Snapshot.student_key.label("student_key"),
            func.avg(Snapshot.file_size).label("avg_bytes"),
            func.count(Snapshot.id).label("snapshot_count"),
        )
        .where(*filters)
        .group_by(Snapshot.student_key)
        .subquery()
    )
    averages = db.exec(
        select(
            func.avg(per_student.c.avg_bytes), func.avg(per_student.c.snapshot_count)
        )
    ).one()
    ranked = (
        select(
            Snapshot.student_key.label("student_key"),
            Snapshot.occurred_at.label("occurred_at"),
            Snapshot.file_size.label("file_size"),
            func.row_number()
            .over(
                partition_by=Snapshot.student_key,
                order_by=(Snapshot.occurred_at.desc(), Snapshot.id.desc()),
            )
            .label("rank"),
        )
        .where(*filters)
        .subquery()
    )
    top = db.exec(
        select(ranked.c.student_key, ranked.c.occurred_at, ranked.c.file_size)
        .where(ranked.c.rank == 1)
        .order_by(ranked.c.occurred_at.desc())
        .limit(7)
    ).all()
    return distribution, averages, top


def get_graph_data(
    db: Session, class_div: str, hw_name: str, start: datetime, end: datetime
):
    previous_size = func.lag(Snapshot.file_size).over(
        partition_by=(Snapshot.student_key, Snapshot.relative_path),
        order_by=(Snapshot.occurred_at, Snapshot.id),
    )
    deltas = (
        select(
            Snapshot.student_key.label("student_key"),
            previous_size.label("previous_size"),
            func.abs(Snapshot.file_size - previous_size).label("size_change"),
        )
        .where(
            *assignment_predicates(Snapshot, class_div, hw_name),
            Snapshot.occurred_at >= start,
            Snapshot.occurred_at <= end,
        )
        .subquery()
    )
    return db.exec(
        select(deltas.c.student_key, func.sum(deltas.c.size_change))
        .where(deltas.c.previous_size.is_not(None))
        .group_by(deltas.c.student_key)
        .order_by(deltas.c.student_key)
    ).all()


def _event_average(db: Session, model, class_div: str, hw_name: str) -> float:
    count, students = db.exec(
        select(
            func.count(model.id), func.count(func.distinct(model.student_key))
        ).where(*assignment_predicates(model, class_div, hw_name))
    ).one()
    return round((count or 0) / students, 2) if students else 0.0


def get_build_avg(db: Session, class_div: str, hw_name: str) -> float:
    return _event_average(db, BuildLog, class_div, hw_name)


def get_run_avg(db: Session, class_div: str, hw_name: str) -> float:
    return _event_average(db, RunLog, class_div, hw_name)
