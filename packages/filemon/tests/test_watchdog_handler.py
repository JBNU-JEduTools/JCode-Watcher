import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call
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
    mock.should_process.return_value = True
    mock.is_directory.return_value = False  # 파일로 간주하여 should_process까지 도달하게 함
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
        handler.path_filter.should_process.assert_called_once_with(mock_fs_event.src_path)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.raw_queue.put_nowait, mock_fs_event
        )

    def test_filtered_file_skipped(self, handler, mock_fs_event):
        """필터링된 파일은 스킵"""
        # Given
        handler.path_filter.should_process.return_value = False

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process.assert_called_once_with(mock_fs_event.src_path)
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
        handler.path_filter.should_process.assert_called_once_with(mock_fs_event.src_path)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.raw_queue.put_nowait, mock_fs_event
        )

    def test_filtered_path_skipped(self, handler, mock_fs_event):
        """필터링된 경로는 스킵"""
        # Given
        handler.path_filter.should_process.return_value = False

        # When
        handler.on_deleted(mock_fs_event)

        # Then
        handler.path_filter.should_process.assert_called_once_with(mock_fs_event.src_path)
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
    """on_moved 메서드 테스트 - moved 이벤트를 deleted + modified로 분리"""

    def test_both_paths_valid(self, handler, mock_moved_event):
        """src_path와 dest_path 모두 유효한 경우 - 두 이벤트 모두 생성"""
        # Given
        handler.path_filter.should_process.return_value = True
        
        # When
        handler.on_moved(mock_moved_event)

        # Then
        # src_path와 dest_path 둘 다 검증되어야 함
        expected_calls = [
            call(mock_moved_event.src_path),
            call(mock_moved_event.dest_path)
        ]
        handler.path_filter.should_process.assert_has_calls(expected_calls)
        
        # 두 번의 큐 전송이 있어야 함 (deleted + modified)
        assert handler.loop.call_soon_threadsafe.call_count == 2
        
        # 첫 번째 호출: deleted 이벤트
        first_call = handler.loop.call_soon_threadsafe.call_args_list[0]
        deleted_event = first_call[0][1]  # put_nowait의 두 번째 인자
        assert deleted_event.event_type == "deleted"
        assert deleted_event.src_path == mock_moved_event.src_path
        
        # 두 번째 호출: modified 이벤트
        second_call = handler.loop.call_soon_threadsafe.call_args_list[1]
        modified_event = second_call[0][1]
        assert modified_event.event_type == "modified" 
        assert modified_event.src_path == mock_moved_event.dest_path

    def test_only_src_path_valid(self, handler, mock_moved_event):
        """src_path만 유효한 경우 - 삭제 이벤트만 생성"""
        # Given
        def should_process_side_effect(path):
            return path == mock_moved_event.src_path  # src_path만 True
            
        handler.path_filter.should_process.side_effect = should_process_side_effect
        
        # When
        handler.on_moved(mock_moved_event)

        # Then
        assert handler.loop.call_soon_threadsafe.call_count == 1
        
        # deleted 이벤트만 생성되어야 함
        call_args = handler.loop.call_soon_threadsafe.call_args
        event = call_args[0][1]
        assert event.event_type == "deleted"
        assert event.src_path == mock_moved_event.src_path

    def test_only_dest_path_valid(self, handler, mock_moved_event):
        """dest_path만 유효한 경우 - 수정 이벤트만 생성"""
        # Given
        def should_process_side_effect(path):
            return path == mock_moved_event.dest_path  # dest_path만 True
            
        handler.path_filter.should_process.side_effect = should_process_side_effect
        
        # When
        handler.on_moved(mock_moved_event)

        # Then
        assert handler.loop.call_soon_threadsafe.call_count == 1
        
        # modified 이벤트만 생성되어야 함
        call_args = handler.loop.call_soon_threadsafe.call_args
        event = call_args[0][1]
        assert event.event_type == "modified"
        assert event.src_path == mock_moved_event.dest_path

    def test_no_valid_paths(self, handler, mock_moved_event):
        """src_path와 dest_path 모두 유효하지 않은 경우 - 이벤트 없음"""
        # Given
        handler.path_filter.should_process.return_value = False
        
        # When
        handler.on_moved(mock_moved_event)

        # Then
        handler.loop.call_soon_threadsafe.assert_not_called()

    def test_no_dest_path(self, handler):
        """dest_path가 없는 경우 - src_path만 처리"""
        # Given
        class MockEventWithoutDestPath:
            def __init__(self, src_path):
                self.src_path = src_path
        
        mock_event = MockEventWithoutDestPath('/test/old.c')
        handler.path_filter.should_process.return_value = True
        
        # When
        handler.on_moved(mock_event)

        # Then
        # src_path만 검증되고 deleted 이벤트만 생성
        handler.path_filter.should_process.assert_called_once_with(mock_event.src_path)
        assert handler.loop.call_soon_threadsafe.call_count == 1
        
        call_args = handler.loop.call_soon_threadsafe.call_args
        event = call_args[0][1]
        assert event.event_type == "deleted"

    @patch('app.watchdog_handler.logger')
    def test_exception_handling(self, mock_logger, handler, mock_moved_event):
        """예외 처리 테스트"""
        # Given
        handler.path_filter.should_process.side_effect = RuntimeError("Filter error")

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