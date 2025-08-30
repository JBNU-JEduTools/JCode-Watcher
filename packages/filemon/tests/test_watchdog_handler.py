import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from watchdog.events import FileSystemEvent

from app.watchdog_handler import WatchdogHandler
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo


@pytest.fixture
def mock_event_queue():
    """Mock asyncio Queue"""
    return Mock()


@pytest.fixture
def mock_loop():
    """Mock asyncio event loop"""
    return Mock(spec=asyncio.AbstractEventLoop)


@pytest.fixture
def mock_parser():
    """Mock SourcePathParser"""
    mock = Mock()
    mock.parse.return_value = {
        'class_div': 'class-1',
        'hw_name': 'hw1', 
        'student_id': '202012345',
        'filename': 'test.c'
    }
    return mock


@pytest.fixture
def mock_path_filter():
    """Mock PathFilter"""
    mock = Mock()
    mock.should_process_file.return_value = True
    mock.should_process_path.return_value = True
    return mock


@pytest.fixture
def handler(mock_event_queue, mock_loop, mock_parser, mock_path_filter):
    """WatchdogHandler 인스턴스"""
    return WatchdogHandler(mock_event_queue, mock_loop, mock_parser, mock_path_filter)


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

    @patch('app.watchdog_handler.os.path.getsize')
    @patch('app.watchdog_handler.settings')
    @patch('app.watchdog_handler.SourceFileInfo.from_parsed_data')
    @patch('app.watchdog_handler.FilemonEvent.from_components')
    def test_success_flow(self, mock_filemon_from_components, mock_source_from_parsed_data, 
                         mock_settings, mock_getsize, handler, mock_fs_event):
        """정상 처리 흐름 테스트"""
        # Given
        mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000000
        mock_getsize.return_value = 500
        mock_source_info = Mock()
        mock_source_from_parsed_data.return_value = mock_source_info
        mock_filemon_event = Mock()
        mock_filemon_from_components.return_value = mock_filemon_event

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once_with(mock_fs_event.src_path)
        mock_getsize.assert_called_once_with(mock_fs_event.src_path)
        handler.parser.parse.assert_called_once_with(Path(mock_fs_event.src_path))
        mock_source_from_parsed_data.assert_called_once()
        mock_filemon_from_components.assert_called_once_with(mock_fs_event, mock_source_info)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.event_queue.put_nowait, mock_filemon_event
        )

    def test_filtered_file_skipped(self, handler, mock_fs_event):
        """필터링된 파일은 스킵"""
        # Given
        handler.path_filter.should_process_file.return_value = False

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once_with(mock_fs_event.src_path)
        handler.parser.parse.assert_not_called()
        handler.event_queue.put_nowait.assert_not_called()

    @patch('app.watchdog_handler.os.path.getsize')
    @patch('app.watchdog_handler.settings')
    def test_file_size_exceeded(self, mock_settings, mock_getsize, handler, mock_fs_event):
        """파일 크기 초과시 스킵"""
        # Given
        mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000
        mock_getsize.return_value = 2000

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once()
        mock_getsize.assert_called_once_with(mock_fs_event.src_path)
        handler.parser.parse.assert_not_called()
        handler.event_queue.put_nowait.assert_not_called()

    @patch('app.watchdog_handler.os.path.getsize')
    def test_os_error_handling(self, mock_getsize, handler, mock_fs_event):
        """OSError 처리"""
        # Given
        mock_getsize.side_effect = OSError("File not found")

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once()
        handler.parser.parse.assert_not_called()
        handler.event_queue.put_nowait.assert_not_called()

    @patch('app.watchdog_handler.os.path.getsize')
    @patch('app.watchdog_handler.settings')
    def test_unexpected_error_handling(self, mock_settings, mock_getsize, handler, mock_fs_event):
        """예상치 못한 에러 처리"""
        # Given
        mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000000
        mock_getsize.return_value = 500
        handler.parser.parse.side_effect = ValueError("Parsing error")

        # When
        handler.on_modified(mock_fs_event)

        # Then
        handler.path_filter.should_process_file.assert_called_once()
        handler.parser.parse.assert_called_once()
        handler.event_queue.put_nowait.assert_not_called()


class TestOnDeleted:
    """on_deleted 메서드 테스트"""

    @patch('app.watchdog_handler.SourceFileInfo.from_parsed_data')
    @patch('app.watchdog_handler.FilemonEvent.from_components')
    def test_success_flow(self, mock_filemon_from_components, mock_source_from_parsed_data,
                         handler, mock_fs_event):
        """정상 처리 흐름 테스트"""
        # Given
        mock_source_info = Mock()
        mock_source_from_parsed_data.return_value = mock_source_info
        mock_filemon_event = Mock()
        mock_filemon_from_components.return_value = mock_filemon_event

        # When
        handler.on_deleted(mock_fs_event)

        # Then
        handler.path_filter.should_process_path.assert_called_once_with(mock_fs_event.src_path)
        handler.parser.parse.assert_called_once_with(Path(mock_fs_event.src_path))
        mock_source_from_parsed_data.assert_called_once()
        mock_filemon_from_components.assert_called_once_with(mock_fs_event, mock_source_info)
        handler.loop.call_soon_threadsafe.assert_called_once_with(
            handler.event_queue.put_nowait, mock_filemon_event
        )

    def test_filtered_path_skipped(self, handler, mock_fs_event):
        """필터링된 경로는 스킵"""
        # Given
        handler.path_filter.should_process_path.return_value = False

        # When
        handler.on_deleted(mock_fs_event)

        # Then
        handler.path_filter.should_process_path.assert_called_once_with(mock_fs_event.src_path)
        handler.parser.parse.assert_not_called()
        handler.event_queue.put_nowait.assert_not_called()

    def test_unexpected_error_handling(self, handler, mock_fs_event):
        """예상치 못한 에러 처리"""
        # Given
        handler.parser.parse.side_effect = ValueError("Parsing error")

        # When
        handler.on_deleted(mock_fs_event)

        # Then
        handler.path_filter.should_process_path.assert_called_once()
        handler.parser.parse.assert_called_once()
        handler.event_queue.put_nowait.assert_not_called()


class TestOnMoved:
    """on_moved 메서드 테스트"""

    @patch('app.watchdog_handler.os.path.exists')
    @patch('app.watchdog_handler.os.path.getsize')
    @patch('app.watchdog_handler.settings')
    @patch('app.watchdog_handler.SourceFileInfo.from_parsed_data')
    @patch('app.watchdog_handler.FilemonEvent.from_components')
    @patch('app.watchdog_handler.FileSystemEvent')
    def test_success_flow(self, mock_fs_event_class, mock_filemon_from_components,
                         mock_source_from_parsed_data, mock_settings, mock_getsize,
                         mock_exists, handler, mock_moved_event):
        """정상 처리 흐름 테스트 (삭제 + 수정 이벤트)"""
        # Given
        mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000000
        mock_exists.return_value = True
        mock_getsize.return_value = 500
        
        # Mock FileSystemEvent 인스턴스들 설정
        mock_delete_event = Mock()
        mock_delete_event.src_path = mock_moved_event.src_path  # 문자열로 설정
        mock_modify_event = Mock()
        mock_modify_event.src_path = mock_moved_event.dest_path  # 문자열로 설정
        
        mock_fs_event_class.side_effect = [mock_delete_event, mock_modify_event]
        
        mock_source_info = Mock()
        mock_source_from_parsed_data.return_value = mock_source_info
        mock_filemon_event = Mock()
        mock_filemon_from_components.return_value = mock_filemon_event

        # When
        handler.on_moved(mock_moved_event)

        # Then
        # FileSystemEvent가 두 번 생성되어야 함 (삭제용 + 수정용)
        assert mock_fs_event_class.call_count == 2
        
        # 파싱이 두 번 호출되어야 함 (삭제용 + 수정용)
        assert handler.parser.parse.call_count == 2
        
        # 큐에 두 번 추가되어야 함 (삭제 이벤트 + 수정 이벤트)
        assert handler.loop.call_soon_threadsafe.call_count == 2

    def test_no_dest_path(self, handler):
        """dest_path가 없는 경우"""
        # Given
        mock_event = Mock()
        mock_event.src_path = '/test/old.c'
        del mock_event.dest_path  # dest_path 속성 제거

        # When
        handler.on_moved(mock_event)

        # Then
        # 삭제 이벤트만 처리되고 수정 이벤트는 처리되지 않음
        assert handler.parser.parse.call_count <= 1

    @patch('app.watchdog_handler.os.path.exists')
    def test_dest_path_not_exists(self, mock_exists, handler, mock_moved_event):
        """이동된 파일이 존재하지 않는 경우"""
        # Given
        mock_exists.return_value = False

        # When
        handler.on_moved(mock_moved_event)

        # Then
        mock_exists.assert_called_with(mock_moved_event.dest_path)
        # 삭제 이벤트만 처리됨
        assert handler.parser.parse.call_count <= 1

    @patch('app.watchdog_handler.os.path.exists')
    def test_filtered_file_skipped(self, mock_exists, handler, mock_moved_event):
        """필터링된 파일은 수정 이벤트 스킵"""
        # Given
        mock_exists.return_value = True
        handler.path_filter.should_process_file.return_value = False

        # When
        handler.on_moved(mock_moved_event)

        # Then
        mock_exists.assert_called_with(mock_moved_event.dest_path)
        handler.path_filter.should_process_file.assert_called_with(mock_moved_event.dest_path)
        # 삭제 이벤트만 처리됨
        assert handler.parser.parse.call_count <= 1

    @patch('app.watchdog_handler.os.path.exists')
    @patch('app.watchdog_handler.os.path.getsize')
    @patch('app.watchdog_handler.settings')
    def test_file_size_exceeded(self, mock_settings, mock_getsize, mock_exists, 
                               handler, mock_moved_event):
        """파일 크기 초과시 수정 이벤트 스킵"""
        # Given
        mock_exists.return_value = True
        mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000
        mock_getsize.return_value = 2000

        # When
        handler.on_moved(mock_moved_event)

        # Then
        mock_getsize.assert_called_with(mock_moved_event.dest_path)
        # 삭제 이벤트만 처리됨
        assert handler.parser.parse.call_count <= 1

    @patch('app.watchdog_handler.os.path.exists')
    @patch('app.watchdog_handler.os.path.getsize')
    def test_os_error_handling(self, mock_getsize, mock_exists, handler, mock_moved_event):
        """OSError 처리"""
        # Given
        mock_exists.return_value = True
        mock_getsize.side_effect = OSError("File access error")

        # When
        handler.on_moved(mock_moved_event)

        # Then
        mock_getsize.assert_called_with(mock_moved_event.dest_path)
        # 예외로 인해 처리 중단됨

    def test_unexpected_error_handling(self, handler, mock_moved_event):
        """예상치 못한 에러 처리"""
        # Given
        handler.parser.parse.side_effect = ValueError("Parsing error")

        # When
        handler.on_moved(mock_moved_event)

        # Then
        # 파싱 에러로 인해 처리 중단
        handler.parser.parse.assert_called_once()