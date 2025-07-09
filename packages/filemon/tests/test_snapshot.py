import pytest
import os
import shutil
from pathlib import Path
from datetime import datetime
from src.core.snapshot import SnapshotManager

@pytest.fixture
def temp_dir(tmp_path):
    """테스트용 임시 디렉토리 생성"""
    # /watcher/codes 디렉토리 구조 생성
    watcher_dir = tmp_path / "watcher"
    codes_dir = watcher_dir / "codes"
    codes_dir.mkdir(parents=True)
    
    # 테스트 종료 후 정리
    yield codes_dir.parent
    shutil.rmtree(watcher_dir)

@pytest.fixture
def snapshot_manager(temp_dir):
    """스냅샷 관리자 초기화"""
    snapshots_dir = temp_dir / "snapshots"
    return SnapshotManager(snapshots_dir)

@pytest.fixture
def source_file(temp_dir):
    """테스트용 소스 파일 생성"""
    # 소스 파일 경로 설정
    source_dir = temp_dir / "codes" / "os-1-202012180" / "hw1"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "test.py"
    source_file.write_text("print('test')")
    return source_file

@pytest.mark.asyncio
async def test_has_changed_no_previous_snapshot(snapshot_manager, source_file, temp_dir):
    """이전 스냅샷이 없는 경우 변경 감지 테스트"""
    result = await snapshot_manager.has_changed(str(source_file), base_path=str(temp_dir / "codes"))
    assert result is True

@pytest.mark.asyncio
async def test_has_changed_with_identical_snapshot(snapshot_manager, source_file, temp_dir):
    """동일한 내용의 스냅샷이 있는 경우 변경 감지 테스트"""
    # 먼저 스냅샷 생성
    await snapshot_manager.create_snapshot(str(source_file), base_path=str(temp_dir / "codes"))
    
    # 변경 감지 테스트
    result = await snapshot_manager.has_changed(str(source_file), base_path=str(temp_dir / "codes"))
    assert result is False

@pytest.mark.asyncio
async def test_has_changed_with_different_content(snapshot_manager, source_file, temp_dir):
    """다른 내용의 스냅샷이 있는 경우 변경 감지 테스트"""
    # 먼저 스냅샷 생성
    await snapshot_manager.create_snapshot(str(source_file), base_path=str(temp_dir / "codes"))
    
    # 파일 내용 변경
    source_file.write_text("print('modified')")
    
    # 변경 감지 테스트
    result = await snapshot_manager.has_changed(str(source_file), base_path=str(temp_dir / "codes"))
    assert result is True

@pytest.mark.asyncio
async def test_create_snapshot(snapshot_manager, source_file, temp_dir):
    """스냅샷 생성 테스트"""
    snapshot_path = await snapshot_manager.create_snapshot(str(source_file), base_path=str(temp_dir / "codes"))
    assert Path(snapshot_path).exists()
    assert Path(snapshot_path).read_text() == "print('test')"

@pytest.mark.asyncio
async def test_create_empty_snapshot(snapshot_manager, source_file, temp_dir):
    """빈 스냅샷 생성 테스트"""
    snapshot_path = await snapshot_manager.create_empty_snapshot(str(source_file), base_path=str(temp_dir / "codes"))
    assert Path(snapshot_path).exists()
    assert Path(snapshot_path).read_text() == ""

@pytest.mark.asyncio
async def test_has_changed_with_nonexistent_file(snapshot_manager, temp_dir):
    """존재하지 않는 파일에 대한 변경 감지 테스트"""
    nonexistent_file = temp_dir / "codes" / "nonexistent.py"
    result = await snapshot_manager.has_changed(str(nonexistent_file), base_path=str(temp_dir / "codes"))
    assert result is False

@pytest.mark.asyncio
async def test_create_snapshot_with_nested_path(snapshot_manager, temp_dir):
    """중첩 경로를 가진 파일의 스냅샷 생성 테스트"""
    # 중첩 경로의 소스 파일 생성
    source_dir = temp_dir / "codes" / "os-1-202012180" / "hw1" / "depth1" / "depth2"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "test.py"
    source_file.write_text("print('nested')")
    
    snapshot_path = await snapshot_manager.create_snapshot(str(source_file), base_path=str(temp_dir / "codes"))
    assert Path(snapshot_path).exists()
    assert Path(snapshot_path).read_text() == "print('nested')"
    assert "@" in str(snapshot_path)  # 중첩 경로가 @로 변환되었는지 확인 