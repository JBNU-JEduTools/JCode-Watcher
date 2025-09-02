import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.snapshot import SnapshotManager
from app.models.source_file_info import SourceFileInfo


@pytest.fixture
def snapshot_manager():
    """SnapshotManager 인스턴스"""
    return SnapshotManager()


@pytest.fixture
def mock_source_info():
    """Mock SourceFileInfo"""
    mock = Mock(spec=SourceFileInfo)
    mock.class_div = 'os-1'
    mock.hw_name = 'hw1'
    mock.student_id = '202012345'
    mock.filename = 'test.c'
    mock.target_file_path = Path('/watch/root/os-1-202012345/hw1/test.c')
    return mock


@pytest.fixture
def mock_nested_source_info():
    """Mock SourceFileInfo for nested path"""
    mock = Mock(spec=SourceFileInfo)
    mock.class_div = 'java-2'
    mock.hw_name = 'hw2' 
    mock.student_id = '202098765'
    mock.filename = 'src@main@Main.java'
    mock.target_file_path = Path('/watch/root/java-2-202098765/hw2/src/main/Main.java')
    return mock


class TestSnapshotManager:
    """SnapshotManager 테스트"""

    @patch('pathlib.Path.mkdir')
    @patch('app.snapshot.aiofiles.open')
    @patch('app.snapshot.datetime')
    @patch('app.snapshot.settings')
    @pytest.mark.asyncio
    async def test_create_snapshot_with_data_success(self, mock_settings, mock_datetime, 
                                                    mock_aiofiles_open, mock_mkdir,
                                                    snapshot_manager, mock_source_info):
        """데이터로 스냅샷 생성 성공"""
        # Given
        mock_settings.SNAPSHOT_BASE = Path('/snapshots')
        mock_datetime.now.return_value.strftime.return_value = '20240830_123456'
        
        mock_file = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file
        
        test_data = b'test file content'
        
        # When
        await snapshot_manager.create_snapshot_with_data(mock_source_info, test_data)
        
        # Then
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        expected_path = Path('/snapshots/os-1/hw1/202012345/test.c/20240830_123456.c')
        mock_aiofiles_open.assert_called_once_with(expected_path, 'wb')
        mock_file.write.assert_called_once_with(test_data)

    @patch('pathlib.Path.mkdir')
    @patch('app.snapshot.aiofiles.open')
    @patch('app.snapshot.datetime')
    @patch('app.snapshot.settings')
    @pytest.mark.asyncio
    async def test_create_snapshot_with_nested_path(self, mock_settings, mock_datetime,
                                                   mock_aiofiles_open, mock_mkdir,
                                                   snapshot_manager, mock_nested_source_info):
        """중첩 경로에서 스냅샷 생성"""
        # Given
        mock_settings.SNAPSHOT_BASE = Path('/snapshots')
        mock_datetime.now.return_value.strftime.return_value = '20240830_123456'
        
        mock_file = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file
        
        test_data = b'public class Main {}'
        
        # When
        await snapshot_manager.create_snapshot_with_data(mock_nested_source_info, test_data)
        
        # Then
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        expected_path = Path('/snapshots/java-2/hw2/202098765/src@main@Main.java/20240830_123456.java')
        mock_aiofiles_open.assert_called_once_with(expected_path, 'wb')
        mock_file.write.assert_called_once_with(test_data)

    @patch('pathlib.Path.mkdir')
    @patch('app.snapshot.aiofiles.open')
    @patch('app.snapshot.datetime')
    @patch('app.snapshot.settings')
    @pytest.mark.asyncio
    async def test_create_empty_snapshot_with_info_success(self, mock_settings, 
                                                          mock_datetime, mock_aiofiles_open, mock_mkdir,
                                                          snapshot_manager, mock_source_info):
        """빈 스냅샷 생성 성공""" 
        # Given
        mock_settings.SNAPSHOT_BASE = Path('/snapshots')
        mock_datetime.now.return_value.strftime.return_value = '20240830_123456'
        
        mock_file = AsyncMock()
        mock_aiofiles_open.return_value.__aenter__.return_value = mock_file
        
        # When
        await snapshot_manager.create_empty_snapshot_with_info(mock_source_info)
        
        # Then
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        expected_path = Path('/snapshots/os-1/hw1/202012345/test.c/20240830_123456.c')
        mock_aiofiles_open.assert_called_once_with(expected_path, 'wb')
        mock_file.write.assert_not_called()  # 빈 파일이므로 write 호출 없음

    @patch('pathlib.Path.mkdir')
    @patch('app.snapshot.aiofiles.open')
    @patch('app.snapshot.logger')
    @pytest.mark.asyncio
    async def test_create_snapshot_with_exception(self, mock_logger, mock_aiofiles_open, mock_mkdir,
                                                   snapshot_manager, mock_source_info):
        """스냅샷 생성 중 예외 발생 시 로그 및 재발생 확인"""
        # Given
        test_exception = OSError("Permission denied")
        mock_aiofiles_open.side_effect = test_exception
        
        # When & Then
        # Check if the correct exception is raised
        with pytest.raises(OSError, match="Permission denied"):
            await snapshot_manager.create_snapshot_with_data(mock_source_info, b'data')
        
        # Check that mkdir was still called
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Check that the logger was called with the correct arguments
        mock_logger.error.assert_called_once()
        call_args, call_kwargs = mock_logger.error.call_args
        assert "스냅샷 파일 생성 실패" in call_args[0]
        assert call_kwargs['filename'] == mock_source_info.filename
        assert call_kwargs['error'] == str(test_exception)

    @patch('app.snapshot.settings')
    def test_get_snapshot_path_simple(self, mock_settings, snapshot_manager, mock_source_info):
        """단순 경로에서 스냅샷 경로 생성"""
        # Given
        mock_settings.SNAPSHOT_BASE = Path('/snapshots')
        timestamp = '20240830_123456'
        
        # When
        result = snapshot_manager._get_snapshot_path(mock_source_info, timestamp)
        
        # Then
        expected = Path('/snapshots/os-1/hw1/202012345/test.c/20240830_123456.c')
        assert result == expected

    @patch('app.snapshot.settings')
    def test_get_snapshot_path_with_nested(self, mock_settings, snapshot_manager, mock_nested_source_info):
        """중첩 경로에서 스냅샷 경로 생성"""
        # Given
        mock_settings.SNAPSHOT_BASE = Path('/snapshots')
        timestamp = '20240830_123456'
        
        # When
        result = snapshot_manager._get_snapshot_path(mock_nested_source_info, timestamp)
        
        # Then
        expected = Path('/snapshots/java-2/hw2/202098765/src@main@Main.java/20240830_123456.java')
        assert result == expected

    def test_get_nested_path_simple_file(self, snapshot_manager, mock_source_info):
        """단순 파일의 중첩 경로"""
        # When
        result = snapshot_manager._get_nested_path(mock_source_info)
        
        # Then
        # hw1 디렉토리 다음의 모든 경로 파트가 @로 연결되어야 함
        expected = 'test.c'
        assert result == expected

    def test_get_nested_path_nested_file(self, snapshot_manager, mock_nested_source_info):
        """중첩된 파일의 중첩 경로"""
        # When
        result = snapshot_manager._get_nested_path(mock_nested_source_info)
        
        # Then
        expected = 'src@main@Main.java'
        assert result == expected

    def test_get_nested_path_hw_not_found(self, snapshot_manager):
        """과제 디렉토리를 찾을 수 없는 경우"""
        # Given
        mock_info = Mock(spec=SourceFileInfo)
        mock_info.hw_name = 'nonexistent_hw'
        mock_info.target_file_path = Path('/watch/root/os-1-202012345/hw1/test.c')
        
        # When & Then
        with pytest.raises(ValueError, match="과제 디렉토리를 찾을 수 없음"):
            snapshot_manager._get_nested_path(mock_info)
