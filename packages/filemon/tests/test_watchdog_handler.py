import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from watchdog.events import FileSystemEvent

from app.watchdog_handler import WatchdogHandler


@pytest.fixture
def mock_raw_queue():
    """Mock asyncio Queue"""
    return Mock()


@pytest.fixture  
def mock_loop():
    """Mock asyncio event loop"""
    return Mock(spec=asyncio.AbstractEventLoop)


@pytest.fixture
def mock_path_filter():
    """Mock PathFilter"""
    mock = Mock()
    mock.should_process_file.return_value = True
    mock.should_process_path.return_value = True
    return mock


@pytest.fixture
def handler(mock_raw_queue, mock_loop, mock_path_filter):
    """WatchdogHandler 인스턴스"""
    return WatchdogHandler(mock_raw_queue, mock_loop, mock_path_filter)


@pytest.fixture
def mock_fs_event():
    """Mock FileSystemEvent"""
    event = Mock(spec=FileSystemEvent)
    event.src_path = '/test/path/class-1/hw1/202012345/test.c'
    return event


@pytest.fixture
def mock_moved_event():
    """Mock FileSystemEvent for moved events"""
    event = Mock(spec=FileSystemEvent)
    event.src_path = '/test/path/class-1/hw1/202012345/old_test.c'
    event.dest_path = '/test/path/class-1/hw1/202012345/new_test.c'
    return event


class TestOnModified:
    """on_modified 메서드 테스트"""

    def test_success_flow(self, handler, mock_fs_event):
        """정상 처리 흐름 테스트"""
        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once_with(mock_fs_event.src_path)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.raw_queue.put_nowait, mock_fs_event
        )

    def test_filtered_file_skipped(self, handler, mock_fs_event):
        """필터링된 파일은 스킵"""
        # Given
        handler.path_filter.should_process_file.return_value = False

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once_with(mock_fs_event.src_path)
        handler.loop.call_soon_threadsafe.assert_not_called()

    @patch('app.watchdog_handler.logger')
    def test_exception_handling(self, mock_logger, handler, mock_fs_event):
        """예외 처리 테스트"""
        # Given
        handler.loop.call_soon_threadsafe.side_effect = RuntimeError("Queue error")

        # When
        handler.on_modified(mock_fs_event)

        # Then
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args
        assert "on_modified 처리 중 예상치 못한 오류 발생" in error_call_args[0][0]
        assert error_call_args[1]['src_path'] == mock_fs_event.src_path
        assert error_call_args[1]['exc_info'] == True


class TestOnDeleted:
    """on_deleted 메서드 테스트"""

    def test_success_flow(self, handler, mock_fs_event):
        """정상 처리 흐름 테스트"""
        # When
        handler.on_deleted(mock_fs_event)

        # Then
        handler.path_filter.should_process_path.assert_called_once_with(mock_fs_event.src_path)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.raw_queue.put_nowait, mock_fs_event
        )

    def test_filtered_path_skipped(self, handler, mock_fs_event):
        """필터링된 경로는 스킵"""
        # Given
        handler.path_filter.should_process_path.return_value = False

        # When
        handler.on_deleted(mock_fs_event)

        # Then
        handler.path_filter.should_process_path.assert_called_once_with(mock_fs_event.src_path)
        handler.loop.call_soon_threadsafe.assert_not_called()

    @patch('app.watchdog_handler.logger')
    def test_exception_handling(self, mock_logger, handler, mock_fs_event):
        """예외 처리 테스트"""
        # Given
        handler.loop.call_soon_threadsafe.side_effect = RuntimeError("Queue error")

        # When
        handler.on_deleted(mock_fs_event)

        # Then
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args
        assert "on_deleted 처리 중 예상치 못한 오류 발생" in error_call_args[0][0]
        assert error_call_args[1]['src_path'] == mock_fs_event.src_path
        assert error_call_args[1]['exc_info'] == True


class TestOnMoved:
    """on_moved 메서드 테스트"""

    def test_success_flow(self, handler, mock_moved_event):
        """정상 처리 흐름 테스트"""
        # When
        handler.on_moved(mock_moved_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once_with(mock_moved_event.dest_path)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.raw_queue.put_nowait, mock_moved_event
        )

    def test_filtered_file_skipped(self, handler, mock_moved_event):
        """필터링된 파일은 스킵"""
        # Given
        handler.path_filter.should_process_file.return_value = False

        # When
        handler.on_moved(mock_moved_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once_with(mock_moved_event.dest_path)
        handler.loop.call_soon_threadsafe.assert_not_called()

    def test_no_dest_path(self, handler):
        """dest_path가 없는 경우 (src_path 사용)"""
        # Given
        # dest_path 속성이 없는 객체 생성
        class MockEventWithoutDestPath:
            def __init__(self, src_path):
                self.src_path = src_path
        
        mock_event = MockEventWithoutDestPath('/test/old.c')
        
        # When
        handler.on_moved(mock_event)

        # Then
        # dest_path가 없으면 src_path를 사용
        handler.path_filter.should_process_file.assert_called_once_with(mock_event.src_path)

    @patch('app.watchdog_handler.logger')
    def test_exception_handling(self, mock_logger, handler, mock_moved_event):
        """예외 처리 테스트"""
        # Given
        handler.loop.call_soon_threadsafe.side_effect = RuntimeError("Queue error")

        # When
        handler.on_moved(mock_moved_event)

        # Then
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args
        assert "on_moved 처리 중 예상치 못한 오류 발생" in error_call_args[0][0]
        assert error_call_args[1]['src_path'] == mock_moved_event.src_path
        assert error_call_args[1]['dest_path'] == mock_moved_event.dest_path
        assert error_call_args[1]['exc_info'] == True


class TestWatchdogHandlerInit:
    """WatchdogHandler 초기화 테스트"""

    def test_initialization(self, mock_raw_queue, mock_loop, mock_path_filter):
        """WatchdogHandler 정상 초기화"""
        # When
        handler = WatchdogHandler(mock_raw_queue, mock_loop, mock_path_filter)

        # Then
        assert handler.raw_queue == mock_raw_queue
        assert handler.loop == mock_loop
        assert handler.path_filter == mock_path_filter