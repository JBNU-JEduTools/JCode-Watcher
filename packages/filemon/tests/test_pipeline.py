import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor
from watchdog.events import FileSystemEvent

from app.pipeline import FilemonPipeline
from app.source_path_parser import SourcePathParser
from app.source_path_filter import PathFilter
from app.models.source_file_info import SourceFileInfo
from app.snapshot import SnapshotManager
from app.sender import SnapshotSender


@pytest.fixture
def mock_executor():
    """Mock ThreadPoolExecutor"""
    return Mock(spec=ThreadPoolExecutor)


@pytest.fixture
def mock_snapshot_manager():
    """Mock SnapshotManager"""
    mock = Mock(spec=SnapshotManager)
    mock.create_snapshot_with_data = AsyncMock()
    mock.create_empty_snapshot_with_info = AsyncMock()
    return mock


@pytest.fixture
def mock_parser():
    """Mock SourcePathParser"""
    mock = Mock(spec=SourcePathParser)
    mock.parse.return_value = {
        'class_div': 'os-1',
        'hw_name': 'hw1',
        'student_id': '202012345',
        'filename': 'test.c'
    }
    return mock


@pytest.fixture
def mock_path_filter():
    """Mock PathFilter"""
    return Mock(spec=PathFilter)


@pytest.fixture
def mock_snapshot_sender():
    """Mock SnapshotSender"""
    mock = Mock(spec=SnapshotSender)
    mock.register_snapshot = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def pipeline(mock_executor, mock_snapshot_manager, mock_snapshot_sender, mock_parser, mock_path_filter):
    """FilemonPipeline 인스턴스"""
    return FilemonPipeline(mock_executor, mock_snapshot_manager, mock_snapshot_sender, mock_parser, mock_path_filter)


@pytest.fixture
def mock_fs_event():
    """Mock FileSystemEvent"""
    event = Mock(spec=FileSystemEvent)
    event.event_type = "modified"
    event.src_path = '/watch/root/os-1-202012345/hw1/test.c'
    return event


@pytest.fixture
def mock_deleted_event():
    """Mock FileSystemEvent for deleted"""
    event = Mock(spec=FileSystemEvent)
    event.event_type = "deleted"
    event.src_path = '/watch/root/os-1-202012345/hw1/test.c'
    return event


@pytest.fixture
def mock_moved_event():
    """Mock FileSystemEvent for moved"""
    event = Mock(spec=FileSystemEvent)
    event.event_type = "moved"
    event.src_path = '/watch/root/os-1-202012345/hw1/old_test.c'
    event.dest_path = '/watch/root/os-1-202012345/hw1/new_test.c'
    return event


class TestFilemonPipeline:
    """FilemonPipeline 테스트"""

    @pytest.mark.asyncio
    async def test_process_event_modified_success(self, pipeline, mock_fs_event, mock_snapshot_manager):
        """수정 이벤트 성공적 처리"""
        # Given
        test_data = b'#include <stdio.h>\nint main() { return 0; }'
        
        with patch('app.pipeline.os.path.getsize') as mock_getsize, \
             patch('app.pipeline.settings') as mock_settings, \
             patch('app.pipeline.SourceFileInfo.from_parsed_data') as mock_source_from_data, \
             patch.object(pipeline.snapshot_sender, 'register_snapshot', new_callable=AsyncMock) as mock_register, \
             patch('app.pipeline.asyncio.wrap_future') as mock_wrap_future:
            
            mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000000
            mock_getsize.return_value = 500
            mock_stat = Mock(st_size=len(test_data), st_mtime=1234567890)
            
            # asyncio.wrap_future 모킹으로 실제 파일 읽기 우회
            async def mock_future_result():
                return (mock_stat, test_data)
            
            coro = mock_future_result()
            mock_wrap_future.return_value = coro
            
            mock_source_info = Mock()
            mock_source_info.filename = 'test.c'
            mock_source_from_data.return_value = mock_source_info
            mock_register.return_value = True
            
            # When
            await pipeline.process_event(mock_fs_event)
        
        # Then
        pipeline.parser.parse.assert_called_once_with(Path(mock_fs_event.src_path))
        mock_source_from_data.assert_called_once()
        pipeline.executor.submit.assert_called_once()
        mock_snapshot_manager.create_snapshot_with_data.assert_called_once_with(mock_source_info, test_data)
        mock_register.assert_called_once_with(mock_source_info, len(test_data))

    @pytest.mark.asyncio
    async def test_process_event_deleted_success(self, pipeline, mock_deleted_event, mock_snapshot_manager):
        """삭제 이벤트 성공적 처리"""
        # Given
        with patch('app.pipeline.SourceFileInfo.from_parsed_data') as mock_source_from_data, \
             patch.object(pipeline.snapshot_sender, 'register_snapshot', new_callable=AsyncMock) as mock_register:
            
            mock_source_info = Mock()
            mock_source_info.filename = 'test.c'
            mock_source_from_data.return_value = mock_source_info
            mock_register.return_value = True
            
            # When
            await pipeline.process_event(mock_deleted_event)
        
        # Then
        pipeline.parser.parse.assert_called_once_with(Path(mock_deleted_event.src_path))
        mock_source_from_data.assert_called_once()
        mock_snapshot_manager.create_empty_snapshot_with_info.assert_called_once_with(mock_source_info)
        mock_register.assert_called_once_with(mock_source_info, 0)


    @pytest.mark.asyncio
    async def test_process_event_modified_file_size_exceeded(self, pipeline, mock_fs_event):
        """수정 이벤트 - 파일 크기 초과"""
        # Given
        with patch('app.pipeline.os.path.getsize') as mock_getsize, \
             patch('app.pipeline.settings') as mock_settings:
            
            mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000
            mock_getsize.return_value = 2000
            
            # When
            await pipeline.process_event(mock_fs_event)
        
        # Then
        mock_getsize.assert_called_once_with(mock_fs_event.src_path)
        pipeline.parser.parse.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_event_modified_file_not_found(self, pipeline, mock_fs_event, mock_snapshot_manager):
        """수정 이벤트 - 파일 없음"""
        # Given
        with patch('app.pipeline.os.path.getsize') as mock_getsize, \
             patch('app.pipeline.settings') as mock_settings, \
             patch('app.pipeline.SourceFileInfo.from_parsed_data') as mock_source_from_data, \
             patch('app.pipeline.asyncio.wrap_future') as mock_wrap_future:
            
            mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000000
            mock_getsize.return_value = 500
            
            # Future에서 FileNotFoundError 발생하도록 설정
            async def mock_future_error():
                raise FileNotFoundError("File not found")
            mock_wrap_future.return_value = mock_future_error()
            
            mock_source_info = Mock()
            mock_source_from_data.return_value = mock_source_info
            
            # When
            await pipeline.process_event(mock_fs_event)
        
        # Then
        pipeline.executor.submit.assert_called_once()
        mock_snapshot_manager.create_snapshot_with_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_event_modified_runtime_error(self, pipeline, mock_fs_event, mock_snapshot_manager):
        """수정 이벤트 - 읽기 중 파일 변경"""
        # Given
        with patch('app.pipeline.os.path.getsize') as mock_getsize, \
             patch('app.pipeline.settings') as mock_settings, \
             patch('app.pipeline.SourceFileInfo.from_parsed_data') as mock_source_from_data, \
             patch('app.pipeline.asyncio.wrap_future') as mock_wrap_future:
            
            mock_settings.MAX_CAPTURABLE_FILE_SIZE = 1000000
            mock_getsize.return_value = 500
            
            # Future에서 RuntimeError 발생하도록 설정
            async def mock_future_error():
                raise RuntimeError("file changed during read")
            mock_wrap_future.return_value = mock_future_error()
            
            mock_source_info = Mock()
            mock_source_from_data.return_value = mock_source_info
            
            # When
            await pipeline.process_event(mock_fs_event)
        
        # Then
        pipeline.executor.submit.assert_called_once()
        mock_snapshot_manager.create_snapshot_with_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_event_unknown_event_type(self, pipeline):
        """알 수 없는 이벤트 타입"""
        # Given
        unknown_event = Mock(spec=FileSystemEvent)
        unknown_event.event_type = "unknown"
        unknown_event.src_path = "/test/path"
        
        # When
        await pipeline.process_event(unknown_event)
        
        # Then
        pipeline.parser.parse.assert_not_called()

    @patch('builtins.open')
    @patch('app.pipeline.os.fstat')
    def test_read_and_verify_success(self, mock_fstat, mock_open, pipeline):
        """파일 읽기 및 검증 성공"""
        # Given
        mock_file = Mock()
        mock_open.return_value = mock_file
        mock_file.fileno.return_value = 3
        
        mock_stat_before = Mock()
        mock_stat_before.st_size = 100
        mock_stat_before.st_mtime = 1234567890
        
        mock_stat_after = Mock()
        mock_stat_after.st_size = 100
        mock_stat_after.st_mtime = 1234567890
        
        mock_fstat.side_effect = [mock_stat_before, mock_stat_after]
        
        test_data = b'test file content'
        mock_file.read.return_value = test_data
        
        target_path = "/test/path/file.txt"
        
        # When
        with patch('app.pipeline.Path') as mock_path_class:
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path
            
            result = pipeline.read_and_verify(target_path)
        
        # Then
        stat_result, data = result
        assert stat_result == mock_stat_after
        assert data == test_data
        mock_open.assert_called_once_with(mock_path, "rb", buffering=0)
        mock_file.close.assert_called_once()
        assert mock_fstat.call_count == 2

    @patch('builtins.open')
    @patch('app.pipeline.os.fstat')
    def test_read_and_verify_file_changed_during_read(self, mock_fstat, mock_open, pipeline):
        """파일 읽기 중 변경된 경우"""
        # Given
        mock_file = Mock()
        mock_open.return_value = mock_file
        mock_file.fileno.return_value = 3
        
        mock_stat_before = Mock()
        mock_stat_before.st_size = 100
        mock_stat_before.st_mtime = 1234567890
        
        mock_stat_after = Mock()
        mock_stat_after.st_size = 200  # 크기 변경됨
        mock_stat_after.st_mtime = 1234567890
        
        mock_fstat.side_effect = [mock_stat_before, mock_stat_after]
        mock_file.read.return_value = b'test content'
        
        target_path = "/test/path/file.txt"
        
        # When & Then
        with patch('app.pipeline.Path') as mock_path_class:
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path
            
            with pytest.raises(RuntimeError, match="file changed during read"):
                pipeline.read_and_verify(target_path)
            
            mock_file.close.assert_called_once()

    def test_read_and_verify_file_not_exists(self, pipeline):
        """파일이 존재하지 않는 경우"""
        # Given
        target_path = "/nonexistent/file.txt"
        
        # When & Then
        with patch('app.pipeline.Path') as mock_path_class:
            mock_path = Mock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path
            
            with pytest.raises(FileNotFoundError):
                pipeline.read_and_verify(target_path)

    @patch('builtins.open')
    def test_read_and_verify_file_close_in_finally(self, mock_open, pipeline):
        """파일이 finally 블록에서 닫히는지 확인"""
        # Given
        mock_file = Mock()
        mock_open.return_value = mock_file
        mock_file.fileno.return_value = 3
        mock_file.read.side_effect = IOError("Read error")
        
        target_path = "/test/path/file.txt"
        
        # When & Then
        with patch('app.pipeline.Path') as mock_path_class:
            mock_path = Mock()
            mock_path.exists.return_value = True
            mock_path_class.return_value = mock_path
            
            with pytest.raises(IOError):
                pipeline.read_and_verify(target_path)
            
            mock_file.close.assert_called_once()


class TestFilemonPipelineInit:
    """FilemonPipeline 초기화 테스트"""

    def test_initialization(self, mock_executor, mock_snapshot_manager, mock_snapshot_sender, mock_parser, mock_path_filter):
        """FilemonPipeline 정상 초기화"""
        # When
        pipeline = FilemonPipeline(mock_executor, mock_snapshot_manager, mock_snapshot_sender, mock_parser, mock_path_filter)

        # Then
        assert pipeline.executor == mock_executor
        assert pipeline.snapshot_manager == mock_snapshot_manager
        assert pipeline.snapshot_sender == mock_snapshot_sender
        assert pipeline.parser == mock_parser
        assert pipeline.path_filter == mock_path_filter
        assert pipeline.snapshot_sender is not None