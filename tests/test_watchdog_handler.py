import pytest
import re
import asyncio
import os
import shutil
from pathlib import Path
from datetime import datetime
from watchdog.events import FileModifiedEvent, FileDeletedEvent, FileMovedEvent
from src.core.watchdog_handler import WatchdogHandler, WatcherEvent
from src.config.settings import SOURCE_PATTERNS, IGNORE_PATTERNS, MAX_FILE_SIZE

def check_path_pattern(path: str) -> bool:
    """주어진 경로가 허용된 패턴과 일치하는지 테스트합니다."""
    # 먼저 무시 패턴과 매칭되는지 확인
    for pattern in IGNORE_PATTERNS:
        if re.match(pattern, path):
            return False
    
    # 허용 패턴과 매칭되는지 확인
    for pattern in SOURCE_PATTERNS:
        if re.match(pattern, path):
            return True
    
    return False

class TestWatchdogHandler:
    @pytest.mark.parametrize("path_str,expected", [
        # 유효한 경로 테스트
        ("/watcher/codes/os-1-202012180/hw1/test.c", True),          # 0depth
        ("/watcher/codes/os-1-202012180/hw5/1/test.py", True),       # 1depth
        ("/watcher/codes/os-1-202012180/hw8/1/2/test.h", True),      # 2depth
        ("/watcher/codes/os-1-202012180/hw10/1/2/3/test.c", False),  # 3depth (불가)
        
        # 무효한 경로 테스트
        ("/watcher/codes/os-1-202012180/hw0/test.c", False),         # hw0 (불가)
        ("/watcher/codes/os-1-202012180/hw11/test.c", False),        # hw11 (불가)
        ("/watcher/codes/os-1-202012180/hw1/1/2/3/4/test.c", False), # 4depth (불가)
        ("/watcher/codes/os-1-202012180/hw1/test.cpp", False),       # 잘못된 확장자
        ("/watcher/codes/os-1-202012180/hw1/test.pyc", False),       # 컴파일된 파일
        ("/watcher/codes/os-1-202012180/hw1/.git/test.py", False),   # 숨김 디렉토리
    ])
    def test_path_patterns(self, path_str, expected):
        """경로 패턴 테스트"""
        assert check_path_pattern(path_str) == expected

    @pytest.mark.parametrize("hw_number", [
        *range(1, 11)  # hw1부터 hw10까지
    ])
    def test_valid_hw_numbers(self, hw_number):
        path_str = f"/watcher/codes/os-1-202012180/hw{hw_number}/test.c"
        assert check_path_pattern(path_str)

    @pytest.mark.parametrize("hw_number", [
        0, 11, 12, 20, 99
    ])
    def test_invalid_hw_numbers(self, hw_number):
        path_str = f"/watcher/codes/os-1-202012180/hw{hw_number}/test.c"
        assert not check_path_pattern(path_str)

    @pytest.mark.parametrize("extension", [
        "c", "h", "py"
    ])
    def test_valid_extensions(self, extension):
        path_str = f"/watcher/codes/os-1-202012180/hw1/test.{extension}"
        assert check_path_pattern(path_str)

    @pytest.mark.parametrize("extension", [
        "cpp", "hpp", "java", "go", "js", "pyc", "pyo", "pyd"
    ])
    def test_invalid_extensions(self, extension):
        path_str = f"/watcher/codes/os-1-202012180/hw1/test.{extension}"
        assert not check_path_pattern(path_str)

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
def source_dir(temp_dir):
    """테스트용 소스 디렉토리 생성"""
    source_dir = temp_dir / "codes" / "os-1-202012180" / "hw1"
    source_dir.mkdir(parents=True)
    return source_dir

@pytest.fixture
async def event_queue():
    """이벤트 큐 생성"""
    queue = asyncio.Queue()
    yield queue
    # cleanup: 남은 이벤트 모두 처리
    while not queue.empty():
        try:
            queue.get_nowait()
            queue.task_done()
        except asyncio.QueueEmpty:
            break

@pytest.fixture
async def handler(event_queue, temp_dir):
    """WatchdogHandler 인스턴스 생성"""
    codes_dir = temp_dir / "codes"
    loop = asyncio.get_running_loop()
    handler = WatchdogHandler(event_queue, loop, base_path=str(codes_dir))
    yield handler
    # cleanup: 모든 이벤트가 처리될 때까지 대기 (최대 2초)
    try:
        await asyncio.wait_for(event_queue.join(), timeout=2.0)
    except asyncio.TimeoutError:
        # 타임아웃 발생 시 남은 이벤트 강제 처리
        while not event_queue.empty():
            try:
                event_queue.get_nowait()
                event_queue.task_done()
            except asyncio.QueueEmpty:
                break

def test_watcher_event_from_watchdog_event(temp_dir):
    """WatcherEvent 생성 테스트"""
    codes_dir = temp_dir / "codes"  # watcher 디렉토리를 제거
    source_path = str(codes_dir / "os-1-202012180/hw1/test.py")
    event = FileModifiedEvent(source_path)
    
    watcher_event = WatcherEvent.from_watchdog_event(event, base_path=str(codes_dir))
    
    assert watcher_event.event_type == "modified"
    assert watcher_event.source_path == source_path
    assert watcher_event.dest_path is None
    assert isinstance(watcher_event.timestamp, datetime)
    assert watcher_event.path_info.class_div == "os-1"
    assert watcher_event.path_info.student_id == "202012180"
    assert watcher_event.path_info.hw_name == "hw1"
    assert watcher_event.path_info.filename == "test.py"

@pytest.mark.asyncio
async def test_on_modified(handler, source_dir):
    """수정 이벤트 처리 테스트"""
    # 테스트 파일 생성
    test_file = source_dir / "test.py"
    test_file.write_text("print('test')")
    
    # 이벤트 생성 및 처리
    event = FileModifiedEvent(str(test_file))
    handler.on_modified(event)
    
    # 이벤트 큐에서 이벤트 확인
    watcher_event = await handler.event_queue.get()
    assert watcher_event.event_type == "modified"
    assert watcher_event.source_path == str(test_file)
    assert watcher_event.dest_path is None

@pytest.mark.asyncio
async def test_on_deleted(handler, source_dir):
    """삭제 이벤트 처리 테스트"""
    # 테스트 파일 생성
    test_file = source_dir / "test.py"
    test_file.write_text("print('test')")
    
    # 이벤트 생성 및 처리
    event = FileDeletedEvent(str(test_file))
    handler.on_deleted(event)
    
    # 이벤트 큐에서 이벤트 확인
    watcher_event = await handler.event_queue.get()
    assert watcher_event.event_type == "deleted"
    assert watcher_event.source_path == str(test_file)
    assert watcher_event.dest_path is None

@pytest.mark.asyncio
async def test_on_moved(handler, source_dir):
    """이동 이벤트 처리 테스트"""
    # 테스트 파일 생성
    src_file = source_dir / "old.py"
    dest_file = source_dir / "new.py"
    src_file.write_text("print('test')")
    
    # 실제로 파일 이동
    src_file.rename(dest_file)
    
    # 이벤트 생성 및 처리
    event = FileMovedEvent(str(src_file), str(dest_file))
    handler.on_moved(event)
    
    try:
        # 삭제 이벤트 확인
        delete_event = await asyncio.wait_for(handler.event_queue.get(), timeout=1.0)
        assert delete_event.event_type == "deleted"
        assert delete_event.source_path == str(src_file)
        handler.event_queue.task_done()
        
        # 수정 이벤트 확인
        modify_event = await asyncio.wait_for(handler.event_queue.get(), timeout=1.0)
        assert modify_event.event_type == "modified"
        assert modify_event.source_path == str(dest_file)
        handler.event_queue.task_done()
    except asyncio.TimeoutError:
        pytest.fail("이벤트 처리 시간 초과")

@pytest.mark.asyncio
async def test_on_modified_large_file(handler, source_dir):
    """큰 파일 수정 이벤트 처리 테스트"""
    # 큰 파일 생성
    test_file = source_dir / "large.py"
    test_file.write_bytes(b'0' * (MAX_FILE_SIZE + 1))
    
    # 이벤트 생성 및 처리
    event = FileModifiedEvent(str(test_file))
    handler.on_modified(event)
    
    # 큐가 비어있는지 확인
    assert handler.event_queue.empty()

@pytest.mark.asyncio
async def test_on_moved_large_file(handler, source_dir):
    """큰 파일 이동 이벤트 처리 테스트"""
    # 큰 파일 생성
    src_file = source_dir / "old.py"
    dest_file = source_dir / "new.py"
    src_file.write_bytes(b'0' * (MAX_FILE_SIZE + 1))
    
    # 실제로 파일 이동
    src_file.rename(dest_file)
    
    # 이벤트 생성 및 처리
    event = FileMovedEvent(str(src_file), str(dest_file))
    handler.on_moved(event)
    
    try:
        # 삭제 이벤트만 확인 (수정 이벤트는 파일 크기로 인해 무시됨)
        delete_event = await asyncio.wait_for(handler.event_queue.get(), timeout=1.0)
        assert delete_event.event_type == "deleted"
        assert delete_event.source_path == str(src_file)
        handler.event_queue.task_done()
        
        # 큐가 비어있는지 확인
        assert handler.event_queue.empty()
    except asyncio.TimeoutError:
        pytest.fail("이벤트 처리 시간 초과") 