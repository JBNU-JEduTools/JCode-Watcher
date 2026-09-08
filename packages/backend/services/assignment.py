from datetime import datetime

from crud.assignment import (
    get_build_avg,
    get_graph_data,
    get_monitoring_summary,
    get_run_avg,
)
from schemas.assignment import BuildAvgResponse, RunAvgResponse
from sqlmodel import Session


def calculate_monitoring_data(db: Session, class_div: str, hw_name: str):
    distribution, averages, top = get_monitoring_summary(db, class_div, hw_name)
    percentile_90, percentile_50 = distribution
    avg_bytes, avg_num = averages
    if percentile_90 is None:
        return None
    return {
        "percentile_90": round(float(percentile_90), 2),
        "percentile_50": round(float(percentile_50), 2),
        "avg_bytes": round(float(avg_bytes or 0), 2),
        "avg_num": round(float(avg_num or 0), 2),
        "top_7": [
            {
                "student_num": student_key,
                "timestamp": occurred_at.isoformat(),
                "code_size": file_size,
            }
            for student_key, occurred_at, file_size in top
        ],
    }


async def fetch_total_graph_data(
    db: Session, class_div: str, hw_name: str, start: datetime, end: datetime
):
    rows = get_graph_data(db, class_div, hw_name, start, end)
    return {
        "results": [
            {"student_num": key, "size_change": float(change or 0)}
            for key, change in rows
        ]
    }


def calculate_build_avg(db: Session, class_div: str, hw_name: str) -> BuildAvgResponse:
    return BuildAvgResponse(avg_count=get_build_avg(db, class_div, hw_name))


def calculate_run_avg(db: Session, class_div: str, hw_name: str) -> RunAvgResponse:
    return RunAvgResponse(avg_count=get_run_avg(db, class_div, hw_name))
