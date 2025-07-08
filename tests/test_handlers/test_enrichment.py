import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
import asyncio

from src.handlers.enrichment import EnrichmentHandler
from src.events.models import EventBuilder, EventMetadata, ProcessTypeInfo
from src.bpf.event import RawBpfEvent
from src.process.types import ProcessType

@pytest.fixture
def raw_event():
    """테스트용 RawBpfEvent를 생성합니다."""
    return RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/gcc",
        cwd="/home/student",
        args="gcc main.c -o main",
        error_flags="0",
        exit_code=0
    )

@pytest.fixture
def event_builder(raw_event):
    """ProcessTypeInfo가 설정된 EventBuilder를 생성합니다."""
    builder = EventBuilder(raw_event)
    builder.process = ProcessTypeInfo(type=ProcessType.GCC)
    return builder

@pytest.fixture
def handler():
    """EnrichmentHandler 인스턴스를 생성합니다."""
    return EnrichmentHandler()

@pytest.fixture
def invalid_raw_event():
    """잘못된 호스트네임을 가진 RawBpfEvent를 생성합니다."""
    return RawBpfEvent(
        hostname="invalid-hostname",
        pid=1234,
        binary_path="/usr/bin/gcc",
        cwd="/home/student",
        args="gcc main.c -o main",
        error_flags="0",
        exit_code=0
    )

@pytest.fixture
def invalid_event_builder(invalid_raw_event):
    """잘못된 호스트네임을 가진 EventBuilder를 생성합니다."""
    builder = EventBuilder(invalid_raw_event)
    builder.process = ProcessTypeInfo(type=ProcessType.GCC)
    return builder

@pytest.mark.asyncio
async def test_parse_hostname_success(handler):
    """호스트네임 파싱 성공 케이스를 테스트합니다."""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        binary_path="/usr/bin/gcc",
        args="gcc -o test test.c",
        pid=1234,
        cwd="/home/test",
        error_flags="0",
        exit_code=0
    ))
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(event)
    
    # Then
    assert result is not None
    assert result.metadata is not None
    assert result.metadata.class_div == "os-1"
    assert result.metadata.student_id == "202012180"
    next_handler.handle.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_parse_hostname_invalid_format(handler):
    """잘못된 호스트네임 형식을 테스트합니다."""
    # Given
    invalid_hostnames = [
        "invalid",
        "jcode-os",
        "jcode-os-1",
        "wrong-os-1-202012180-hash"
    ]
    
    # When/Then
    for hostname in invalid_hostnames:
        event = EventBuilder(base=RawBpfEvent(
            hostname=hostname,
            binary_path="/usr/bin/gcc",
            args="gcc -o test test.c",
            pid=1234,
            cwd="/home/test",
            error_flags="0",
            exit_code=0
        ))
        result = await handler.handle(event)
        assert result is None

@pytest.mark.asyncio
async def test_handle_success(handler, event_builder):
    """이벤트 처리 성공 케이스를 테스트합니다."""
    # Given
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(event_builder)
    
    # Then
    assert result == event_builder
    assert isinstance(result.metadata, EventMetadata)
    assert result.metadata.class_div == "os-1"
    assert result.metadata.student_id == "202012180"
    assert isinstance(result.metadata.timestamp, datetime)
    assert result.metadata.timestamp.tzinfo == timezone.utc
    
    # 다음 핸들러 호출 확인
    next_handler.handle.assert_awaited_once_with(event_builder)

@pytest.mark.asyncio
async def test_handle_invalid_hostname(handler, invalid_event_builder):
    """잘못된 호스트네임으로 인한 처리 실패를 테스트합니다."""
    # Given
    next_handler = Mock()
    next_handler.handle = AsyncMock()
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(invalid_event_builder)
    
    # Then
    assert result is None
    next_handler.handle.assert_not_called() 