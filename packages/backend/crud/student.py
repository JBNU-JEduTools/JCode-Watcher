from datetime import datetime

from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from sqlalchemy import func
from sqlmodel import Session, select
from utils.assignment_key import assignment_predicates
from utils.cursor import event_cursor_predicate


def get_snapshot_stats(
    db: Session, class_div: str, hw_name: str, student_id: int, filename: str
):
    return db.exec(
        select(func.count(Snapshot.id), func.avg(Snapshot.file_size)).where(
            *assignment_predicates(Snapshot, class_div, hw_name),
            Snapshot.student_key == str(student_id),
            Snapshot.relative_path == filename,
        )
    ).one()


def get_assignment_snapshot_stats(
    db: Session, class_div: str, student_id: int, hw_name: str
):
    filters = (
        *assignment_predicates(Snapshot, class_div, hw_name),
        Snapshot.student_key == str(student_id),
    )
    count, average, first, last = db.exec(
        select(
            func.count(Snapshot.id),
            func.avg(Snapshot.file_size),
            func.min(Snapshot.occurred_at),
            func.max(Snapshot.occurred_at),
        ).where(*filters)
    ).one()
    latest = db.exec(
        select(Snapshot.occurred_at)
        .where(*filters)
        .order_by(Snapshot.occurred_at.desc(), Snapshot.id.desc())
        .limit(2)
    ).all()
    return count, average, first, last, latest


def get_student_trends(
    db: Session, class_div: str, student_id: int, hw_name: str, interval: int
):
    bucket_seconds = interval * 60
    bucket = func.to_timestamp(
        func.floor(func.extract("epoch", Snapshot.occurred_at) / bucket_seconds)
        * bucket_seconds
    )
    previous_size = func.lag(Snapshot.file_size, 1, 0).over(
        partition_by=Snapshot.relative_path,
        order_by=(Snapshot.occurred_at, Snapshot.id),
    )
    changes = (
        select(
            bucket.label("bucket"),
            (Snapshot.file_size - previous_size).label("size_change"),
        )
        .where(
            *assignment_predicates(Snapshot, class_div, hw_name),
            Snapshot.student_key == str(student_id),
        )
        .subquery()
    )
    bucket_changes = (
        select(
            changes.c.bucket,
            func.sum(changes.c.size_change).label("size_change"),
        )
        .group_by(changes.c.bucket)
        .subquery()
    )
    total_size = func.sum(bucket_changes.c.size_change).over(
        order_by=bucket_changes.c.bucket, rows=(None, 0)
    )
    return db.exec(
        select(
            bucket_changes.c.bucket,
            total_size.label("total_size"),
            bucket_changes.c.size_change,
        ).order_by(bucket_changes.c.bucket)
    ).all()


def get_build_log(
    db: Session,
    class_div: str,
    hw_name: str,
    student_id: int,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = 200,
    cursor: str | None = None,
):
    statement = select(BuildLog).where(
        *assignment_predicates(BuildLog, class_div, hw_name),
        BuildLog.student_key == str(student_id),
    )
    if from_time is not None:
        statement = statement.where(BuildLog.occurred_at >= from_time)
    if to_time is not None:
        statement = statement.where(BuildLog.occurred_at <= to_time)
    if cursor is not None:
        statement = statement.where(event_cursor_predicate(BuildLog, cursor))
    return db.exec(
        statement.order_by(BuildLog.occurred_at.desc(), BuildLog.id.desc()).limit(
            limit + 1
        )
    ).all()


def get_run_log(
    db: Session,
    class_div: str,
    hw_name: str,
    student_id: int,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = 200,
    cursor: str | None = None,
):
    statement = select(RunLog).where(
        *assignment_predicates(RunLog, class_div, hw_name),
        RunLog.student_key == str(student_id),
    )
    if from_time is not None:
        statement = statement.where(RunLog.occurred_at >= from_time)
    if to_time is not None:
        statement = statement.where(RunLog.occurred_at <= to_time)
    if cursor is not None:
        statement = statement.where(event_cursor_predicate(RunLog, cursor))
    return db.exec(
        statement.order_by(RunLog.occurred_at.desc(), RunLog.id.desc()).limit(limit + 1)
    ).all()
