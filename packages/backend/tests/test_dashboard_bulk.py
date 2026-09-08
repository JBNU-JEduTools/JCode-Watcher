from datetime import datetime, timedelta, timezone
from uuid import uuid4

from crud.dashboard import get_dashboard_summaries
from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

COMMON = dict(
    course_id=7,
    assignment_id=42,
    student_key="1",
    class_div="os-1",
    hw_name="assignment-42",
)


def test_dashboard_aggregates_all_students_in_database():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    now = datetime(2026, 8, 18, 10, tzinfo=timezone.utc)
    with Session(engine) as session:
        session.add_all(
            [
                BuildLog(
                    **COMMON,
                    event_id=uuid4(),
                    occurred_at=now,
                    cwd="/",
                    binary_path="a",
                    cmdline="cc",
                    exit_code=1,
                    target_path="a",
                ),
                BuildLog(
                    **COMMON,
                    event_id=uuid4(),
                    occurred_at=now + timedelta(minutes=1),
                    cwd="/",
                    binary_path="a",
                    cmdline="cc",
                    exit_code=0,
                    target_path="a",
                ),
                RunLog(
                    **COMMON,
                    event_id=uuid4(),
                    occurred_at=now + timedelta(minutes=2),
                    cmdline="./a",
                    exit_code=0,
                    cwd="/",
                    target_path="a",
                    process_type="binary",
                ),
                Snapshot(
                    **COMMON,
                    event_id=uuid4(),
                    occurred_at=now,
                    relative_path="main.c",
                    file_size=100,
                ),
                Snapshot(
                    **COMMON,
                    event_id=uuid4(),
                    occurred_at=now + timedelta(minutes=1),
                    relative_path="main.c",
                    file_size=140,
                ),
            ]
        )
        session.commit()
        result = get_dashboard_summaries(session, "os-1", "assignment-42", [1, 2])

    assert result[1]["build_count"] == 2
    assert result[1]["build_fail_count"] == 1
    assert result[1]["run_count"] == 1
    assert result[1]["total_size_change"] == 140
    assert result[2]["build_count"] == 0
