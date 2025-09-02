
import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from watchdog.events import FileModifiedEvent, FileDeletedEvent, FileMovedEvent

from app.debouncer import Debouncer

# 테스트를 위한 설정값
TEST_DEBOUNCE_WINDOW = 0.1  # 100ms
TEST_DEBOUNCE_MAX_WAIT = 0.5  # 500ms


@pytest.fixture
def mock_settings(mocker):
    """settings 모듈을 모킹하여 테스트용 값으로 대체"""
    mocker.patch('app.debouncer.settings.DEBOUNCE_WINDOW', TEST_DEBOUNCE_WINDOW)
    mocker.patch('app.debouncer.settings.DEBOUNCE_MAX_WAIT', TEST_DEBOUNCE_MAX_WAIT)


@pytest.fixture
def processed_queue():
    """테스트용 비동기 큐"""
    return asyncio.Queue()


@pytest.fixture
def debouncer(processed_queue):
    """테스트용 Debouncer 인스턴스"""
    return Debouncer(processed_queue)


def create_mock_event(event_type, src_path, dest_path=None):
    """Mock watchdog 이벤트를 생성"""
    event_map = {
        "modified": FileModifiedEvent(src_path),
        "deleted": FileDeletedEvent(src_path),
        "moved": FileMovedEvent(src_path, dest_path),
    }
    return event_map[event_type]


@pytest.mark.asyncio
async def test_basic_debouncing(mock_settings, debouncer, processed_queue):
    """여러 개의 modified 이벤트가 하나의 이벤트로 디바운싱되는지 테스트"""
    event1 = create_mock_event("modified", "/test/file.txt")
    event2 = create_mock_event("modified", "/test/file.txt")

    await debouncer.process_event(event1)
    await debouncer.process_event(event2)

    await asyncio.sleep(TEST_DEBOUNCE_WINDOW + 0.05)

    assert processed_queue.qsize() == 1
    result_event = await processed_queue.get()
    assert result_event == event2  # 마지막 이벤트가 처리되어야 함


@pytest.mark.asyncio
async def test_timer_reset(mock_settings, debouncer, processed_queue):
    """새 이벤트가 들어오면 디바운스 타이머가 리셋되는지 테스트"""
    event1 = create_mock_event("modified", "/test/file.txt")
    event2 = create_mock_event("modified", "/test/file.txt")

    await debouncer.process_event(event1)
    await asyncio.sleep(TEST_DEBOUNCE_WINDOW / 2)
    await debouncer.process_event(event2)
    await asyncio.sleep(TEST_DEBOUNCE_WINDOW / 2)

    # 타이머가 리셋되었으므로 아직 이벤트가 없어야 함
    assert processed_queue.qsize() == 0

    # 리셋된 타이머가 만료될 때까지 기다림
    await asyncio.sleep(TEST_DEBOUNCE_WINDOW / 2 + 0.05)

    assert processed_queue.qsize() == 1
    result_event = await processed_queue.get()
    assert result_event == event2


@pytest.mark.asyncio
async def test_immediate_event_with_pending_bucket(mock_settings, debouncer, processed_queue):
    """보류 중인 modified 버킷이 있을 때 deleted 이벤트가 올 경우의 순서를 테스트"""
    modified_event = create_mock_event("modified", "/test/file.txt")
    deleted_event = create_mock_event("deleted", "/test/file.txt")

    # Modified 이벤트를 보내 디바운싱 시작
    await debouncer.process_event(modified_event)

    # 바로 Deleted 이벤트를 보냄
    await debouncer.process_event(deleted_event)

    # 즉시 처리되어야 함
    assert processed_queue.qsize() == 2

    # 순서 확인: modified가 먼저, deleted가 나중에
    result1 = await processed_queue.get()
    result2 = await processed_queue.get()

    assert result1 == modified_event
    assert result2 == deleted_event


@pytest.mark.asyncio
async def test_immediate_event_without_pending_bucket(mock_settings, debouncer, processed_queue):
    """보류 중인 버킷이 없을 때 deleted 이벤트 처리 테스트"""
    deleted_event = create_mock_event("deleted", "/test/file.txt")

    await debouncer.process_event(deleted_event)

    # 잠시 기다릴 필요 없이 즉시 처리되어야 함
    assert processed_queue.qsize() == 1
    result = await processed_queue.get()
    assert result == deleted_event


@pytest.mark.asyncio
async def test_max_wait(mock_settings, debouncer, processed_queue, mocker):
    """DEBOUNCE_MAX_WAIT 기능이 동작하는지 테스트"""
    # DEBOUNCE_WINDOW를 길게 설정하여, 일반 타이머가 만료되지 않도록 함
    mocker.patch('app.debouncer.settings.DEBOUNCE_WINDOW', 10.0)

    event1 = create_mock_event("modified", "/test/file.txt")
    event2 = create_mock_event("modified", "/test/file.txt")
    event3_after_max_wait = create_mock_event("modified", "/test/file.txt")

    # 1. 이벤트를 보내 버킷을 생성. 타이머는 10초 후에 만료되도록 설정됨
    await debouncer.process_event(event1)
    await debouncer.process_event(event2)

    # 2. MAX_WAIT(0.5초) 시간이 지나도록 기다림. 10초짜리 타이머는 아직 유효함
    await asyncio.sleep(TEST_DEBOUNCE_MAX_WAIT + 0.05)

    # 3. 이 시점까지 큐는 비어있어야 함
    assert processed_queue.qsize() == 0

    # 4. 새로운 이벤트를 보내 _add_to_bucket의 MAX_WAIT 확인 로직을 트리거
    await debouncer.process_event(event3_after_max_wait)

    # 5. MAX_WAIT 규칙에 따라 이전 버킷(event2 포함)이 플러시되어야 함
    assert processed_queue.qsize() == 1
    result = await processed_queue.get()
    assert result == event2


@pytest.mark.asyncio
async def test_independent_paths(mock_settings, debouncer, processed_queue):
    """서로 다른 경로의 이벤트가 독립적으로 처리되는지 테스트"""
    event_a = create_mock_event("modified", "/test/file_a.txt")
    event_b = create_mock_event("modified", "/test/file_b.txt")

    await debouncer.process_event(event_a)
    await asyncio.sleep(TEST_DEBOUNCE_WINDOW / 2)
    await debouncer.process_event(event_b)

    # A의 타이머가 먼저 만료되어야 함
    await asyncio.sleep(TEST_DEBOUNCE_WINDOW / 2 + 0.05)

    assert processed_queue.qsize() == 1
    result1 = await processed_queue.get()
    assert result1 == event_a

    # B의 타이머가 만료되기를 기다림
    await asyncio.sleep(TEST_DEBOUNCE_WINDOW / 2)

    assert processed_queue.qsize() == 1
    result2 = await processed_queue.get()
    assert result2 == event_b
