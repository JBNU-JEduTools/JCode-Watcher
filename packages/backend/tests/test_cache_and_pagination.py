from datetime import datetime, timezone
from uuid import uuid4

from crud.student import get_build_log
from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from utils.assignment_key import assignment_id_from_hw_name
from utils.cache import BoundedTTLCache, cache, invalidate_log_cache, log_cache_key
from utils.cursor import encode_event_cursor


def test_v2_workspace_key_uses_immutable_assignment_id():
    assert assignment_id_from_hw_name("assignment-42") == 42
    assert assignment_id_from_hw_name("homework-42") is None
    assert assignment_id_from_hw_name("assignment-42-renamed") is None


def build_event(index: int, occurred_at: datetime) -> BuildLog:
    return BuildLog(
        event_id=uuid4(),
        course_id=7,
        assignment_id=42,
        student_key="1",
        class_div="os-1",
        hw_name="assignment-42",
        occurred_at=occurred_at,
        cwd="/workspace",
        binary_path="a.out",
        cmdline="gcc main.c",
        exit_code=0,
        target_path="main.c",
    )


def test_cache_is_bounded_and_prefix_invalidation_is_targeted():
    bounded = BoundedTTLCache(max_entries=2)
    bounded.set("a", 1)
    bounded.set("b", 2)
    bounded.set("c", 3)
    assert bounded.get("a") is None

    key = log_cache_key("build", "os-1", "assignment-42", 1, None, None, 100, None)
    cache.set(key, ["stale"])
    invalidate_log_cache("build", "os-1", "assignment-42", 1)
    assert cache.get(key) is None


def test_build_log_query_is_bounded_and_cursor_is_stable():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add_all(
            [build_event(index, now) for index in range(5)]
        )
        session.commit()
        first = get_build_log(session, "os-1", "assignment-42", 1, limit=2)
        second = get_build_log(
            session,
            "os-1",
            "assignment-42",
            1,
            limit=2,
            cursor=encode_event_cursor(first[1].occurred_at, first[1].id),
        )
    assert [row.id for row in first[:2]] == [5, 4]
    assert [row.id for row in second[:2]] == [3, 2]


def test_postgresql_query_indexes_are_declared():
    index_names = {
        index.name
        for model in (Snapshot, BuildLog, RunLog)
        for index in model.__table__.indexes
    }
    assert index_names == {
        "ix_snapshot_assignment_student_file_time",
        "ix_snapshot_assignment_student_time",
        "ix_snapshot_assignment_time",
        "ix_build_assignment_student_time",
        "ix_build_assignment_time",
        "ix_run_assignment_student_time",
        "ix_run_assignment_time",
    }
