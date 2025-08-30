import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from app.pipeline import FilemonPipeline
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo
from app.snapshot import SnapshotManager


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
def pipeline(mock_executor, mock_snapshot_manager):
    """FilemonPipeline 인스턴스"""
    return FilemonPipeline(mock_executor, mock_snapshot_manager)


@pytest.fixture
def real_source_info():
    """실제 SourceFileInfo 객체"""
    return SourceFileInfo(
        class_div='os-1',
        hw_name='hw1',
        student_id='202012345',
        filename='test.c',
        target_file_path=Path('/watch/root/os-1-202012345/hw1/test.c')
    )


@pytest.fixture
def real_modified_event(real_source_info):
    """실제 FilemonEvent for modified event"""
    return FilemonEvent(
        event_type="modified",
        target_file_path="/watch/root/os-1-202012345/hw1/test.c",
        dest_path=None,  # modified 이벤트는 dest_path 없음
        timestamp=datetime.now(),
        source_file_info=real_source_info
    )


@pytest.fixture
def real_deleted_event(real_source_info):
    """실제 FilemonEvent for deleted event"""
    return FilemonEvent(
        event_type="deleted",
        target_file_path="/watch/root/os-1-202012345/hw1/test.c",
        dest_path=None,  # deleted 이벤트는 dest_path 없음
        timestamp=datetime.now(),
        source_file_info=real_source_info
    )


class TestFilemonPipeline:
    """FilemonPipeline 테스트"""

    @pytest.mark.asyncio
    async def test_process_event_modified_success(self, real_modified_event, mock_snapshot_manager):
        """수정 이벤트 성공적 처리 - 실제 데이터 흐름 검증"""
        # Given
        pipeline = FilemonPipeline(Mock(), mock_snapshot_manager)
        test_data = b'#include <stdio.h>\nint main() { return 0; }'
        
        # read_and_verify 결과 시뮬레이션 (파일 시스템만 Mock)
        with patch.object(pipeline, 'read_and_verify') as mock_read:
            mock_stat = Mock(st_size=len(test_data), st_mtime=1234567890)
            mock_read.return_value = (mock_stat, test_data)
            
            # When: 실제 이벤트로 실제 로직 실행
            await pipeline.process_event(real_modified_event)
        
        # Then: 데이터 검증 (단순 호출 확인이 아님)
        mock_snapshot_manager.create_snapshot_with_data.assert_called_once()
        
        # 실제 전달된 데이터 검증 (핵심!)
        call_args = mock_snapshot_manager.create_snapshot_with_data.call_args[0]
        actual_source_info, actual_data = call_args
        
        assert actual_source_info.student_id == "202012345"
        assert actual_source_info.class_div == "os-1"
        assert actual_source_info.filename == "test.c"
        assert actual_data == test_data

    @pytest.mark.asyncio
    async def test_process_event_deleted_success(self, real_deleted_event, mock_snapshot_manager):
        """삭제 이벤트 성공적 처리 - 실제 데이터 흐름 검증"""
        # Given
        pipeline = FilemonPipeline(Mock(), mock_snapshot_manager)
        
        # When: 실제 이벤트로 실제 로직 실행
        await pipeline.process_event(real_deleted_event)
        
        # Then: 데이터 검증
        mock_snapshot_manager.create_empty_snapshot_with_info.assert_called_once()
        
        # 실제 전달된 데이터 검증
        call_args = mock_snapshot_manager.create_empty_snapshot_with_info.call_args[0]
        actual_source_info = call_args[0]
        
        assert actual_source_info.student_id == "202012345"
        assert actual_source_info.class_div == "os-1"
        assert actual_source_info.filename == "test.c"

    @pytest.mark.parametrize("event_type,expected_method", [
        ("deleted", "create_empty_snapshot_with_info"),
        ("modified", "create_snapshot_with_data"),
    ])
    @pytest.mark.asyncio
    async def test_event_type_routing_logic(self, event_type, expected_method, real_source_info, mock_snapshot_manager):
        """이벤트 타입별 라우팅 로직 검증 - 핵심 비즈니스 로직!"""
        
        # Given: 실제 이벤트 (event_type만 변경)
        event = FilemonEvent(
            event_type=event_type,
            target_file_path="/test/file.c",
            dest_path=None,  # moved가 아니므로 None
            timestamp=datetime.now(),
            source_file_info=real_source_info
        )
        
        pipeline = FilemonPipeline(Mock(), mock_snapshot_manager)
        
        if event_type == "modified":
            # modified의 경우만 파일 읽기 Mock 필요
            with patch.object(pipeline, 'read_and_verify') as mock_read:
                mock_read.return_value = (Mock(), b"test data")
                await pipeline.process_event(event)
        else:
            await pipeline.process_event(event)
        
        # Then: 올바른 메서드가 호출되었는가?
        expected_mock = getattr(mock_snapshot_manager, expected_method)
        expected_mock.assert_called_once()
        
        # 실제 데이터가 올바르게 전달되었는가?
        actual_source_info = expected_mock.call_args[0][0]
        assert actual_source_info.student_id == "202012345"
        assert actual_source_info.class_div == "os-1"

    @pytest.mark.asyncio
    async def test_process_event_file_not_found_error(self, real_modified_event, mock_snapshot_manager):
        """FileNotFoundError 처리 - 실제 예외 흐름 검증"""
        # Given: 실제 이벤트 + 파일 없음 상황
        pipeline = FilemonPipeline(Mock(), mock_snapshot_manager)
        
        with patch.object(pipeline, 'read_and_verify') as mock_read:
            mock_read.side_effect = FileNotFoundError("File not found")
            
            # When: 실제 예외 상황
            await pipeline.process_event(real_modified_event)
        
        # Then: 예외 처리 검증
        # 1. 파일 읽기 시도됨
        mock_read.assert_called_once_with(real_modified_event.target_file_path)
        
        # 2. 스냅샷이 생성되지 않아야 함
        mock_snapshot_manager.create_snapshot_with_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_event_runtime_error(self, real_modified_event, mock_snapshot_manager):
        """RuntimeError 처리 - 파일 읽기 중 변경 검증"""
        # Given: 실제 이벤트 + 파일 읽기 중 변경 상황
        pipeline = FilemonPipeline(Mock(), mock_snapshot_manager)
        
        with patch.object(pipeline, 'read_and_verify') as mock_read:
            mock_read.side_effect = RuntimeError("file changed during read")
            
            # When: 실제 예외 상황
            await pipeline.process_event(real_modified_event)
        
        # Then: 예외 처리 검증
        # 1. 파일 읽기 시도됨
        mock_read.assert_called_once_with(real_modified_event.target_file_path)
        
        # 2. 스냅샷이 생성되지 않아야 함
        mock_snapshot_manager.create_snapshot_with_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_event_unexpected_error(self, real_modified_event, mock_snapshot_manager):
        """예상치 못한 에러 처리 - 일반 Exception 검증"""
        # Given: 실제 이벤트 + 예상치 못한 에러 상황
        pipeline = FilemonPipeline(Mock(), mock_snapshot_manager)
        
        with patch.object(pipeline, 'read_and_verify') as mock_read:
            mock_read.side_effect = ValueError("Unexpected error")
            
            # When: 실제 예외 상황
            await pipeline.process_event(real_modified_event)
        
        # Then: 예외 처리 검증
        # 1. 파일 읽기 시도됨
        mock_read.assert_called_once_with(real_modified_event.target_file_path)
        
        # 2. 스냅샷이 생성되지 않아야 함
        mock_snapshot_manager.create_snapshot_with_data.assert_not_called()

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

    @patch('builtins.open')
    @patch('app.pipeline.os.fstat')
    def test_read_and_verify_mtime_changed(self, mock_fstat, mock_open, pipeline):
        """파일 수정 시간이 변경된 경우"""
        # Given
        mock_file = Mock()
        mock_open.return_value = mock_file
        mock_file.fileno.return_value = 3
        
        mock_stat_before = Mock()
        mock_stat_before.st_size = 100
        mock_stat_before.st_mtime = 1234567890
        
        mock_stat_after = Mock()
        mock_stat_after.st_size = 100
        mock_stat_after.st_mtime = 1234567891  # 수정 시간 변경됨
        
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