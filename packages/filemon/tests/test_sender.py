import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from app.config.settings import settings
from app.models.source_file_info import SourceFileInfo
from app.sender import SnapshotSender


@pytest.fixture
def event():
    return SourceFileInfo(
        class_div="os-1",
        hw_name="assignment-42",
        assignment_id=42,
        student_id="202012345",
        filename="src/main.c",
        target_file_path=Path(
            "/watcher/codes/os-1-202012345/assignment-42/src/main.c"
        ),
        timestamp="20260818_120000",
        event_id=UUID("00000000-0000-0000-0000-000000000042"),
        occurred_at=datetime(2026, 8, 18, 12, tzinfo=timezone.utc),
    )


def response_context(status=200, acknowledged=None, body="error"):
    response = MagicMock(status=status)
    response.text = AsyncMock(return_value=body)
    response.json = AsyncMock(
        return_value={"acknowledged_event_ids": acknowledged or []}
    )
    post_context = MagicMock()
    post_context.__aenter__ = AsyncMock(return_value=response)
    post_context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.post.return_value = post_context
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    return session_context, session


@pytest.mark.asyncio
async def test_snapshot_uses_batch_contract(event, tmp_path):
    resolver = AsyncMock()
    resolver.resolve.return_value = 7
    sender = SnapshotSender(resolver, str(tmp_path / "spool.db"))
    context, session = response_context(acknowledged=[str(event.event_id)])

    with patch("app.sender.aiohttp.ClientSession", return_value=context):
        assert await sender.register_snapshot(event, 128) is True

    url = session.post.call_args.args[0]
    item = session.post.call_args.kwargs["json"]["events"][0]
    assert url.endswith("/api/v2/events/batch")
    assert item["type"] == "snapshot"
    assert item["payload"] == {
        "event_id": str(event.event_id),
        "course_id": 7,
        "assignment_id": 42,
        "student_key": "202012345",
        "class_div": "os-1",
        "hw_name": "assignment-42",
        "relative_path": "src/main.c",
        "file_size": 128,
        "occurred_at": "2026-08-18T12:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_failed_snapshot_survives_restart_with_same_event_id(
    event, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "SPOOL_RETRY_SECONDS", 0)
    resolver = AsyncMock()
    resolver.resolve.return_value = 7
    spool_path = str(tmp_path / "spool.db")
    first = SnapshotSender(resolver, spool_path)
    failed_context, failed_session = response_context(status=503)
    with patch("app.sender.aiohttp.ClientSession", return_value=failed_context):
        assert await first.register_snapshot(event, 128) is False

    restarted = SnapshotSender(resolver, spool_path)
    success_context, success_session = response_context(
        acknowledged=[str(event.event_id)]
    )
    with patch("app.sender.aiohttp.ClientSession", return_value=success_context):
        assert await restarted.flush_once() == 1

    first_id = failed_session.post.call_args.kwargs["json"]["events"][0]["payload"][
        "event_id"
    ]
    retried_id = success_session.post.call_args.kwargs["json"]["events"][0][
        "payload"
    ]["event_id"]
    assert first_id == retried_id == str(event.event_id)
    assert restarted.spool.contains(str(event.event_id)) is False


@pytest.mark.asyncio
async def test_snapshot_is_spooled_when_course_resolution_fails(
    event, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "SPOOL_RETRY_SECONDS", 0)
    resolver = AsyncMock()
    resolver.resolve.side_effect = ValueError("course metadata missing")
    sender = SnapshotSender(resolver, str(tmp_path / "spool.db"))
    assert await sender.register_snapshot(event, 128) is False
    assert sender.spool.contains(str(event.event_id)) is True


@pytest.mark.asyncio
async def test_retry_loop_reports_when_it_has_started(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SPOOL_RETRY_SECONDS", 60)
    sender = SnapshotSender(AsyncMock(), str(tmp_path / "spool.db"))
    sender.flush_once = AsyncMock(return_value=0)
    started = asyncio.Event()
    task = asyncio.create_task(sender.run_retry_loop(started))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        await asyncio.sleep(0)
        sender.flush_once.assert_awaited_once()
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
