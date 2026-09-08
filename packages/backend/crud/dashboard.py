from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from sqlalchemy import case, func
from sqlmodel import Session, select
from utils.assignment_key import assignment_predicates


def _dashboard_summaries(
    db: Session, predicates, student_keys: list[str]
) -> dict[str, dict]:
    unique_keys = list(dict.fromkeys(student_keys))
    summaries = {
        key: {
            "student_key": key,
            "build_count": 0,
            "build_fail_count": 0,
            "run_count": 0,
            "total_size_change": 0,
            "max_single_change": 0,
            "first_activity": None,
            "last_activity": None,
        }
        for key in unique_keys
    }

    build_rows = db.exec(
        select(
            BuildLog.student_key,
            func.count(BuildLog.id),
            func.sum(case((BuildLog.exit_code != 0, 1), else_=0)),
            func.min(BuildLog.occurred_at),
            func.max(BuildLog.occurred_at),
        )
        .where(*predicates(BuildLog), BuildLog.student_key.in_(unique_keys))
        .group_by(BuildLog.student_key)
    ).all()
    for key, count, failed, first, last in build_rows:
        summaries[key].update(
            build_count=count or 0,
            build_fail_count=failed or 0,
            first_activity=first,
            last_activity=last,
        )

    run_rows = db.exec(
        select(
            RunLog.student_key,
            func.count(RunLog.id),
            func.min(RunLog.occurred_at),
            func.max(RunLog.occurred_at),
        )
        .where(*predicates(RunLog), RunLog.student_key.in_(unique_keys))
        .group_by(RunLog.student_key)
    ).all()
    for key, count, first, last in run_rows:
        row = summaries[key]
        row["run_count"] = count or 0
        values = [
            value for value in (row["first_activity"], first) if value is not None
        ]
        row["first_activity"] = min(values) if values else None
        values = [value for value in (row["last_activity"], last) if value is not None]
        row["last_activity"] = max(values) if values else None

    previous_size = func.lag(Snapshot.file_size, 1, 0).over(
        partition_by=(Snapshot.student_key, Snapshot.relative_path),
        order_by=(Snapshot.occurred_at, Snapshot.id),
    )
    deltas = (
        select(
            Snapshot.student_key.label("student_key"),
            Snapshot.occurred_at.label("occurred_at"),
            func.abs(Snapshot.file_size - previous_size).label("size_change"),
        )
        .where(*predicates(Snapshot), Snapshot.student_key.in_(unique_keys))
        .subquery()
    )
    snapshot_rows = db.exec(
        select(
            deltas.c.student_key,
            func.sum(deltas.c.size_change),
            func.max(deltas.c.size_change),
            func.min(deltas.c.occurred_at),
            func.max(deltas.c.occurred_at),
        ).group_by(deltas.c.student_key)
    ).all()
    for key, total_change, max_change, first, last in snapshot_rows:
        row = summaries[key]
        row["total_size_change"] = total_change or 0
        row["max_single_change"] = max_change or 0
        values = [
            value for value in (row["first_activity"], first) if value is not None
        ]
        row["first_activity"] = min(values) if values else None
        values = [value for value in (row["last_activity"], last) if value is not None]
        row["last_activity"] = max(values) if values else None
    return summaries


def get_dashboard_summaries(
    db: Session, class_div: str, hw_name: str, student_ids: list[int]
) -> dict[int, dict]:
    keys = [str(value) for value in student_ids]
    rows = _dashboard_summaries(
        db,
        lambda model: assignment_predicates(model, class_div, hw_name),
        keys,
    )
    return {int(key): {**row, "student_id": int(key)} for key, row in rows.items()}


def get_dashboard_summaries_by_assignment(
    db: Session, assignment_id: int, student_keys: list[str]
) -> dict[str, dict]:
    return _dashboard_summaries(
        db,
        lambda model: (model.assignment_id == assignment_id,),
        student_keys,
    )
