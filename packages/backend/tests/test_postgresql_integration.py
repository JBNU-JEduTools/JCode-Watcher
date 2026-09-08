import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from crud.assignment import get_graph_data
from crud.event import insert_event_once
from crud.student import get_student_trends
from db.connection import db_url, engine
from fastapi.testclient import TestClient
from main import app
from models.buildLog import BuildLog
from models.runLog import RunLog
from models.snapshot import Snapshot
from routers.v2 import event_page_statement
from sqlalchemy import text
from sqlmodel import Session, create_engine, select

pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql", reason="PostgreSQL integration test"
)
NOW = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)


def identity(event_id=None, student_key="202012345", occurred_at=NOW):
    return {
        "event_id": event_id or uuid4(),
        "course_id": 7,
        "assignment_id": 42,
        "student_key": student_key,
        "class_div": "os-1",
        "hw_name": "assignment-42",
        "occurred_at": occurred_at,
    }


def insert_snapshot_in_process(event_id: str) -> bool:
    process_engine = create_engine(db_url, pool_size=1, max_overflow=0)
    with Session(process_engine) as session:
        inserted = insert_event_once(
            session,
            Snapshot,
            {
                **identity(UUID(event_id)),
                "relative_path": "concurrent.c",
                "file_size": 1,
            },
        )
    process_engine.dispose()
    return inserted


@pytest.fixture(autouse=True)
def clean_events():
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE snapshot_event, build_event, run_event RESTART IDENTITY")
        )


def test_three_event_types_and_duplicate_delivery():
    client = TestClient(app)
    event_id = "00000000-0000-0000-0000-000000000042"
    common = {
        "event_id": event_id,
        "course_id": 7,
        "assignment_id": 42,
        "student_key": "202012345",
        "class_div": "os-1",
        "hw_name": "assignment-42",
        "occurred_at": "2026-08-18T12:00:00+00:00",
    }
    snapshot = {**common, "relative_path": "main.c", "file_size": 100}
    assert client.post("/api/v2/events/snapshot", json=snapshot).json() == {
        "inserted": True
    }
    assert client.post("/api/v2/events/snapshot", json=snapshot).json() == {
        "inserted": False
    }

    common["event_id"] = "00000000-0000-0000-0000-000000000043"
    build = {
        **common,
        "cwd": "/workspace",
        "binary_path": "/usr/bin/gcc",
        "cmdline": "gcc main.c",
        "exit_code": 0,
        "target_path": "main.c",
    }
    assert client.post("/api/v2/events/build", json=build).json() == {"inserted": True}

    common["event_id"] = "00000000-0000-0000-0000-000000000044"
    run = {
        **common,
        "cmdline": "./a.out",
        "exit_code": 0,
        "cwd": "/workspace",
        "target_path": "a.out",
        "process_type": "binary",
    }
    assert client.post("/api/v2/events/run", json=run).json() == {"inserted": True}

    assert (
        len(
            client.get("/api/v2/assignments/42/students/202012345/snapshots").json()[
                "items"
            ]
        )
        == 1
    )
    assert (
        len(
            client.get("/api/v2/assignments/42/students/202012345/build").json()[
                "items"
            ]
        )
        == 1
    )
    assert (
        len(client.get("/api/v2/assignments/42/students/202012345/run").json()["items"])
        == 1
    )

    with Session(engine) as session:
        assert len(session.exec(select(Snapshot)).all()) == 1
        assert len(session.exec(select(BuildLog)).all()) == 1
        assert len(session.exec(select(RunLog)).all()) == 1


def test_batch_is_atomic_and_acknowledges_duplicates():
    client = TestClient(app)
    first_id = "00000000-0000-0000-0000-000000000051"
    common = {
        "course_id": 7,
        "assignment_id": 42,
        "student_key": "202012345",
        "class_div": "os-1",
        "hw_name": "assignment-42",
        "occurred_at": "2026-08-18T12:00:00+00:00",
    }
    request = {
        "events": [
            {
                "type": "snapshot",
                "payload": {
                    **common,
                    "event_id": first_id,
                    "relative_path": "main.c",
                    "file_size": 100,
                },
            },
            {
                "type": "build",
                "payload": {
                    **common,
                    "event_id": "00000000-0000-0000-0000-000000000052",
                    "cwd": "/workspace",
                    "binary_path": "/usr/bin/gcc",
                    "cmdline": "gcc main.c",
                    "exit_code": 0,
                    "target_path": "main.c",
                },
            },
            {
                "type": "run",
                "payload": {
                    **common,
                    "event_id": "00000000-0000-0000-0000-000000000053",
                    "cmdline": "./a.out",
                    "exit_code": 0,
                    "cwd": "/workspace",
                    "target_path": "a.out",
                    "process_type": "binary",
                },
            },
        ]
    }
    expected = [item["payload"]["event_id"] for item in request["events"]]
    assert client.post("/api/v2/events/batch", json=request).json() == {
        "acknowledged_event_ids": expected
    }
    assert client.post("/api/v2/events/batch", json=request).json() == {
        "acknowledged_event_ids": expected
    }

    invalid = {"events": [*request["events"], {**request["events"][0]}]}
    invalid["events"][-1] = {
        "type": "snapshot",
        "payload": {
            **common,
            "event_id": "00000000-0000-0000-0000-000000000054",
            "relative_path": "bad.c",
            "file_size": -1,
        },
    }
    assert client.post("/api/v2/events/batch", json=invalid).status_code == 422
    with Session(engine) as session:
        assert len(session.exec(select(Snapshot)).all()) == 1
        assert len(session.exec(select(BuildLog)).all()) == 1
        assert len(session.exec(select(RunLog)).all()) == 1


def test_bulk_dashboard_cursor_and_assignment_index():
    with Session(engine) as session:
        for index in range(30):
            key = str(202012345 + (index % 2))
            occurred = NOW + timedelta(seconds=index)
            session.add(
                Snapshot(
                    **identity(student_key=key, occurred_at=occurred),
                    relative_path="main.c",
                    file_size=index,
                )
            )
            session.add(
                BuildLog(
                    **identity(student_key=key, occurred_at=occurred),
                    cwd="/",
                    binary_path="gcc",
                    cmdline="gcc",
                    exit_code=index % 2,
                    target_path="main.c",
                )
            )
        session.commit()

    client = TestClient(app)
    summary = client.post(
        "/api/v2/assignments/42/dashboard",
        json={"student_keys": ["202012345", "202012346"]},
    )
    assert summary.status_code == 200
    assert [row["build_count"] for row in summary.json()["students"]] == [15, 15]

    assignment = client.get("/api/assignment/renamed-course/assignment-42")
    assert assignment.status_code == 200
    assert assignment.json()["percentile_50"] is not None

    page = client.get("/api/v2/assignments/42/students/202012345/build?limit=5")
    assert page.status_code == 200
    assert len(page.json()["items"]) == 5
    cursor = page.json()["next_cursor"]
    assert cursor

    with engine.connect() as connection:
        connection.execute(text("SET enable_seqscan = off"))
        statement = event_page_statement(
            BuildLog, 42, "202012345", cursor
        ).limit(10)
        sql = str(
            statement.compile(
                dialect=engine.dialect, compile_kwargs={"literal_binds": True}
            )
        )
        plan = "\n".join(
            row[0]
            for row in connection.execute(text(f"EXPLAIN {sql}"))
        )
    assert "Index Scan" in plan
    assert "ix_build_assignment_" in plan
    assert "Seq Scan" not in plan


def test_trends_carry_unchanged_files_and_graph_uses_first_value_as_baseline():
    with Session(engine) as session:
        events = [
            ("main.c", 100, 0),
            ("util.c", 50, 0),
            ("main.c", 120, 10),
            ("util.c", 70, 20),
        ]
        for relative_path, file_size, minutes in events:
            session.add(
                Snapshot(
                    **identity(occurred_at=NOW + timedelta(minutes=minutes)),
                    relative_path=relative_path,
                    file_size=file_size,
                )
            )
        session.commit()
        trends = get_student_trends(
            session, "renamed-course", 202012345, "assignment-42", 10
        )
        graph = get_graph_data(
            session,
            "renamed-course",
            "assignment-42",
            NOW - timedelta(minutes=1),
            NOW + timedelta(minutes=30),
        )

    assert [int(row.total_size) for row in trends] == [150, 170, 190]
    assert [int(row.size_change) for row in trends] == [150, 20, 20]
    assert graph == [("202012345", 40)]


def test_two_backend_processes_insert_without_duplicates():
    duplicate = str(uuid4())
    ids = [duplicate, duplicate, *[str(uuid4()) for _ in range(10)]]
    with ProcessPoolExecutor(
        max_workers=2, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        results = list(pool.map(insert_snapshot_in_process, ids))
    assert sum(results) == 11

    restarted_engine = create_engine(db_url, pool_size=1, max_overflow=0)
    with Session(restarted_engine) as session:
        assert len(session.exec(select(Snapshot)).all()) == 11
    restarted_engine.dispose()
