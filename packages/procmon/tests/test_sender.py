from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from app.config.settings import settings
from app.models.event import Event
from app.models.process_type import ProcessType
from app.sender import EventSender


def make_event(process_type=ProcessType.GCC, event_id=None):
    return Event(
        process_type=process_type,
        homework_dir="assignment-42",
        assignment_id=42,
        student_id="202012345",
        class_div="os-1",
        timestamp=datetime(2026, 8, 18, 12, tzinfo=timezone.utc),
        event_id=event_id
        or UUID("00000000-0000-0000-0000-000000000042"),
        source_file="/workspace/os-1-202012345/assignment-42/main.c",
        exit_code=0,
        args=["gcc", "main.c"],
        cwd="/workspace/os-1-202012345/assignment-42",
        binary_path="/usr/bin/gcc",
    )


def response_context(status=200, acknowledged=None):
    response = MagicMock(status=status)
    response.text = AsyncMock(return_value="error")
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


def sender(tmp_path):
    resolver = AsyncMock()
    resolver.resolve.return_value = 7
    return EventSender(
        "http://watcher", course_resolver=resolver, spool_path=str(tmp_path / "spool.db")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("process_type", "event_type", "process_name"),
    [
        (ProcessType.GCC, "build", None),
        (ProcessType.USER_BINARY, "run", "binary"),
        (ProcessType.PYTHON, "run", "python"),
    ],
)
async def test_process_event_uses_batch_contract(
    tmp_path, process_type, event_type, process_name
):
    event = make_event(process_type)
    client = sender(tmp_path)
    context, session = response_context(acknowledged=[str(event.event_id)])
    with patch("app.sender.aiohttp.ClientSession", return_value=context):
        assert await client.send_event(event) is True

    item = session.post.call_args.kwargs["json"]["events"][0]
    assert item["type"] == event_type
    assert item["payload"]["event_id"] == str(event.event_id)
    assert item["payload"]["course_id"] == 7
    assert item["payload"]["assignment_id"] == 42
    if process_name:
        assert item["payload"]["process_type"] == process_name


@pytest.mark.asyncio
async def test_failed_process_batch_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SPOOL_RETRY_SECONDS", 0)
    first_event = make_event(event_id=uuid4())
    second_event = make_event(ProcessType.USER_BINARY, event_id=uuid4())
    first = sender(tmp_path)
    failed_context, _ = response_context(status=503)
    with patch("app.sender.aiohttp.ClientSession", return_value=failed_context):
        assert await first.send_event(first_event) is False
        assert await first.send_event(second_event) is False

    restarted = sender(tmp_path)
    ids = [str(first_event.event_id), str(second_event.event_id)]
    success_context, session = response_context(acknowledged=ids)
    with patch("app.sender.aiohttp.ClientSession", return_value=success_context):
        assert await restarted.flush_once() == 2

    sent_ids = {
        item["payload"]["event_id"]
        for item in session.post.call_args.kwargs["json"]["events"]
    }
    assert sent_ids == set(ids)
    assert all(not restarted.spool.contains(event_id) for event_id in ids)


@pytest.mark.asyncio
async def test_unknown_event_is_not_spooled(tmp_path):
    client = sender(tmp_path)
    event = make_event(ProcessType.UNKNOWN)
    assert await client.send_event(event) is False
    assert client.spool.contains(str(event.event_id)) is False
