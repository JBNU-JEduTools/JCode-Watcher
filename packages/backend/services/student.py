from crud.student import (
    get_assignment_snapshot_stats,
    get_build_log,
    get_run_log,
    get_snapshot_stats,
    get_student_trends,
)
from fastapi import HTTPException
from schemas.student import BuildLogResponse, RunLogResponse
from sqlmodel import Session
from utils.cache import cache, log_cache_key
from utils.cursor import encode_event_cursor


def calculate_snapshot_avg(
    db: Session, class_div: str, hw_name: str, student_id: int, filename: str
):
    count, average = get_snapshot_stats(db, class_div, hw_name, student_id, filename)
    if not count:
        return None
    return {"snapshot_avg": count, "snapshot_size_avg": round(float(average or 0), 2)}


def calculate_assignment_snapshot_avg(
    db: Session, class_div: str, student_id: int, hw_name: str
):
    count, average, first, last, latest = get_assignment_snapshot_stats(
        db, class_div, student_id, hw_name
    )
    if not count:
        return None
    interval = (latest[0] - latest[1]).total_seconds() if len(latest) > 1 else 0
    return {
        "snapshot_avg": count,
        "snapshot_size_avg": round(float(average or 0), 2),
        "first": first,
        "last": last,
        "total": (last - first).total_seconds(),
        "interval": interval,
    }


async def graph_data_by_minutes(
    db: Session, class_div: str, hw_name: str, student_id: int, interval: int
):
    if interval <= 0:
        raise HTTPException(
            status_code=400, detail="Interval must be a positive integer."
        )
    rows = get_student_trends(db, class_div, student_id, hw_name, interval)
    return {
        "trends": [
            {
                "timestamp": bucket.strftime("%Y%m%d_%H%M"),
                "total_size": float(total_size or 0),
                "size_change": float(size_change or 0),
            }
            for bucket, total_size, size_change in rows
        ]
    }


def fetch_build_log(
    db: Session,
    class_div: str,
    hw_name: str,
    student_id: int,
    from_time=None,
    to_time=None,
    limit: int = 200,
    cursor: str | None = None,
) -> tuple[list[BuildLogResponse], str | None]:
    key = log_cache_key(
        "build", class_div, hw_name, student_id, from_time, to_time, limit, cursor
    )
    cached_result = cache.get(key)
    if cached_result is not None:
        return cached_result
    results = get_build_log(
        db, class_div, hw_name, student_id, from_time, to_time, limit, cursor
    )
    has_more = len(results) > limit
    page = results[:limit]
    items = [
        BuildLogResponse(
            exit_code=result.exit_code,
            cmdline=result.cmdline,
            cwd=result.cwd,
            binary_path=result.binary_path,
            target_path=result.target_path,
            timestamp=result.occurred_at,
            file_size=0,
        )
        for result in page
    ]
    value = (
        items,
        encode_event_cursor(page[-1].occurred_at, page[-1].id)
        if has_more and page
        else None,
    )
    cache.set(key, value, ttl=60)
    return value


def fetch_run_log(
    db: Session,
    class_div: str,
    hw_name: str,
    student_id: int,
    from_time=None,
    to_time=None,
    limit: int = 200,
    cursor: str | None = None,
) -> tuple[list[RunLogResponse], str | None]:
    key = log_cache_key(
        "run", class_div, hw_name, student_id, from_time, to_time, limit, cursor
    )
    cached_result = cache.get(key)
    if cached_result is not None:
        return cached_result
    results = get_run_log(
        db, class_div, hw_name, student_id, from_time, to_time, limit, cursor
    )
    has_more = len(results) > limit
    page = results[:limit]
    items = [
        RunLogResponse(
            cmdline=result.cmdline,
            exit_code=result.exit_code,
            cwd=result.cwd,
            target_path=result.target_path,
            process_type=result.process_type,
            timestamp=result.occurred_at,
            file_size=0,
        )
        for result in page
    ]
    value = (
        items,
        encode_event_cursor(page[-1].occurred_at, page[-1].id)
        if has_more and page
        else None,
    )
    cache.set(key, value, ttl=60)
    return value
