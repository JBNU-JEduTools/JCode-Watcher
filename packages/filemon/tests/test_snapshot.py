import pytest
import shutil
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
from app.snapshot import SnapshotManager
from app.models.source_file_info import SourceFileInfo

@pytest.fixture
def manager(mocker):
    """SnapshotManager 인스턴스를 초기화하고 parser와 settings를 모킹하여 반환합니다."""
    # settings 모듈 모킹
    settings = MagicMock()
    settings.SNAPSHOT_BASE.mkdir.return_value = None
    mocker.patch('app.snapshot.settings', settings)

    snapshot_manager = SnapshotManager()
    
    # 실제 parser 대신 모킹된 parser를 사용합니다.
    snapshot_manager.parser = MagicMock()
    return snapshot_manager

@pytest.fixture
def mock_path_info():
    """테스트용 SourceFileInfo 객체를 반환합니다."""
    return SourceFileInfo(
        class_div="os-1", hw_name="hw1", student_id="202012180",
        filename="hello.c", source_path=Path("/watcher/codes/os-1-202012180/hw1/hello.c")
    )

@pytest.mark.asyncio
async def test_has_changed_no_source_file(manager, mocker):
    """소스 파일이 존재하지 않을 때 False를 반환하는지 테스트"""
    mocker.patch("pathlib.Path.exists", return_value=False)
    assert await manager.has_changed("any/path") is False

@pytest.mark.asyncio
async def test_has_changed_no_snapshot(manager, mock_path_info, mocker):
    """이전 스냅샷이 없을 때 True를 반환하는지 테스트"""
    mocker.patch("pathlib.Path.exists", return_value=True)
    manager.parser.parse.return_value = mock_path_info
    mocker.patch.object(manager, '_get_latest_snapshot', return_value=None)
    
    assert await manager.has_changed(mock_path_info.source_path) is True

@pytest.mark.asyncio
async def test_has_changed_size_mismatch(manager, mock_path_info, mocker):
    """파일 크기가 다를 때 True를 반환하는지 테스트"""
    mocker.patch("pathlib.Path.exists", return_value=True)
    manager.parser.parse.return_value = mock_path_info
    mocker.patch.object(manager, '_get_latest_snapshot', return_value=Path("snapshot/path"))
    
    # stat().st_size가 다른 값을 반환하도록 모킹
    mocker.patch("pathlib.Path.stat", side_effect=[
        MagicMock(st_size=100), # source
        MagicMock(st_size=200)  # snapshot
    ])
    
    assert await manager.has_changed(mock_path_info.source_path) is True

@pytest.mark.asyncio
async def test_has_changed_content_mismatch(manager, mock_path_info, mocker):
    """파일 내용이 다를 때 True를 반환하는지 테스트"""
    mocker.patch("pathlib.Path.exists", return_value=True)
    manager.parser.parse.return_value = mock_path_info
    mocker.patch.object(manager, '_get_latest_snapshot', return_value=Path("snapshot/path"))
    mocker.patch("pathlib.Path.stat", return_value=MagicMock(st_size=100))

    # aiofiles.open이 다른 내용을 읽도록 모킹
    mock_open = mocker.patch("app.snapshot.aiofiles.open")
    mock_open.side_effect = [
        AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(read=AsyncMock(side_effect=[b'abc', b''])))), # source
        AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(read=AsyncMock(side_effect=[b'def', b'']))))  # snapshot
    ]

    assert await manager.has_changed(mock_path_info.source_path) is True

@pytest.mark.asyncio
async def test_has_changed_content_same(manager, mock_path_info, mocker):
    """파일 내용이 같을 때 False를 반환하는지 테스트"""
    mocker.patch("pathlib.Path.exists", return_value=True)
    manager.parser.parse.return_value = mock_path_info
    mocker.patch.object(manager, '_get_latest_snapshot', return_value=Path("snapshot/path"))
    mocker.patch("pathlib.Path.stat", return_value=MagicMock(st_size=100))

    # aiofiles.open이 같은 내용을 읽도록 모킹
    mock_open = mocker.patch("app.snapshot.aiofiles.open")
    mock_open.side_effect = [
        AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(read=AsyncMock(side_effect=[b'abc', b''])))), # source
        AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(read=AsyncMock(side_effect=[b'abc', b'']))))  # snapshot
    ]

    assert await manager.has_changed(mock_path_info.source_path) is False

@pytest.mark.asyncio
async def test_create_snapshot(manager, mock_path_info, mocker):
    """스냅샷 생성 로직 테스트"""
    source_path = mock_path_info.source_path
    snapshot_path = Path("/path/to/snapshot.c")
    manager.parser.parse.return_value = mock_path_info
    manager.parser.get_snapshot_path.return_value = snapshot_path
    
    mock_mkdir = mocker.patch("pathlib.Path.mkdir")
    mock_copy = mocker.patch("asyncio.to_thread")

    result = await manager.create_snapshot(source_path)

    manager.parser.parse.assert_called_once_with(source_path)
    manager.parser.get_snapshot_path.assert_called_once()
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_copy.assert_called_once_with(shutil.copy2, source_path, snapshot_path)
    assert result == str(snapshot_path)

@pytest.mark.asyncio
async def test_create_empty_snapshot(manager, mock_path_info, mocker):
    """빈 스냅샷 생성 로직 테스트"""
    source_path = mock_path_info.source_path
    snapshot_path = Path("/path/to/snapshot.c")
    manager.parser.parse.return_value = mock_path_info
    manager.parser.get_snapshot_path.return_value = snapshot_path
    
    mock_mkdir = mocker.patch("pathlib.Path.mkdir")
    mock_touch = mocker.patch("pathlib.Path.touch")

    result = await manager.create_empty_snapshot(source_path)

    manager.parser.parse.assert_called_once_with(source_path)
    manager.parser.get_snapshot_path.assert_called_once()
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    snapshot_path.touch.assert_called_once()
    assert result == str(snapshot_path)


def test_get_latest_snapshot(manager, mock_path_info, mocker):
    """가장 최근 스냅샷을 찾는 로직 테스트"""
    snapshot_dir = Path("/snapshot/dir")
    manager.parser.get_snapshot_dir.return_value = snapshot_dir
    
    # glob 결과로 반환될 모킹된 Path 객체들
    p1 = MagicMock(spec=Path)
    p1.stat.return_value.st_mtime = 100
    p2 = MagicMock(spec=Path)
    p2.stat.return_value.st_mtime = 300 # 가장 최신
    p3 = MagicMock(spec=Path)
    p3.stat.return_value.st_mtime = 200
    
    mocker.patch('pathlib.Path.exists', return_value=True)
    # pathlib.Path 클래스의 glob 메서드를 모킹합니다.
    mock_glob = mocker.patch('pathlib.Path.glob', return_value=[p1, p2, p3])

    latest = manager._get_latest_snapshot(mock_path_info)

    manager.parser.get_snapshot_dir.assert_called_once_with(mock_path_info)
    mock_glob.assert_called_once_with(f"*{mock_path_info.source_path.suffix}")
    assert latest == p2 # st_mtime이 가장 큰 p2가 반환되어야 함