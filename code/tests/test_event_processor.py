import pytest
import asyncio
import os
import shutil
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import datetime
from src.core.event_processor import EventProcessor, StudentEventHandler
from src.core.watchdog_handler import WatcherEvent
from src.core.path_info import PathInfo

@pytest.fixture
def temp_dir(tmp_path):
    """테스트용 임시 디렉토리 생성"""
    # /watcher/codes 디렉토리 구조 생성
    watcher_dir = tmp_path / "watcher"
    codes_dir = watcher_dir / "codes"
    codes_dir.mkdir(parents=True)
    
    # snapshots 디렉토리도 생성
    snapshots_dir = watcher_dir / "snapshots"
    snapshots_dir.mkdir(parents=True)
    
    # 테스트 종료 후 정리
    yield codes_dir
    shutil.rmtree(watcher_dir)

@pytest.fixture
def snapshots_dir(temp_dir):
    """스냅샷 디렉토리 생성"""
    return temp_dir.parent / "snapshots"

@pytest.fixture
def source_dir(temp_dir):
    """테스트용 소스 디렉토리 생성"""
    source_dir = temp_dir / "os-1-202012180" / "hw1"
    source_dir.mkdir(parents=True)
    return source_dir

@pytest.fixture
def event_queue():
    """이벤트 큐 생성"""
    return asyncio.Queue()

@pytest.fixture
def api_client():
    """Mock API 클라이언트 생성"""
    client = Mock()
    async def mock_register_snapshot(*args, **kwargs):
        return True
    client.register_snapshot.side_effect = mock_register_snapshot
    return client

@pytest.fixture
def snapshot_manager():
    """Mock 스냅샷 매니저 생성"""
    manager = Mock()
    async def mock_has_changed(*args, **kwargs):
        return manager.has_changed.return_value
    async def mock_create_snapshot(*args, **kwargs):
        return manager.create_snapshot.return_value
    async def mock_create_empty_snapshot(*args, **kwargs):
        return manager.create_empty_snapshot.return_value
    manager.has_changed.side_effect = mock_has_changed
    manager.create_snapshot.side_effect = mock_create_snapshot
    manager.create_empty_snapshot.side_effect = mock_create_empty_snapshot
    return manager

@pytest.fixture
def processor(event_queue, api_client, snapshot_manager):
    """이벤트 프로세서 생성"""
    return EventProcessor(event_queue, api_client, snapshot_manager)

@pytest.fixture
def source_file(source_dir):
    """테스트용 소스 파일 생성"""
    source_file = source_dir / "test.py"
    source_file.write_text("print('test')")
    return source_file

@pytest.mark.asyncio
async def test_route_events_creates_student_handler(processor, source_file, temp_dir):
    """학생별 이벤트 핸들러 생성 테스트"""
    # 이벤트 생성
    event = WatcherEvent(
        event_type="modified",
        source_path=str(source_file),
        dest_path=None,
        timestamp=datetime.now(),
        path_info=PathInfo.from_source_path(str(source_file), base_path=str(temp_dir))
    )
    
    # 이벤트 추가
    await processor.event_queue.put(event)
    
    # 라우팅 태스크 시작
    routing_task = asyncio.create_task(processor.route_events())
    
    # 핸들러가 생성될 때까지 대기
    await asyncio.sleep(0.1)
    
    # 핸들러 확인
    assert "202012180" in processor._student_handlers
    assert isinstance(processor._student_handlers["202012180"], StudentEventHandler)
    
    # 태스크 정리
    routing_task.cancel()
    try:
        await routing_task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_process_modified_event(processor, snapshot_manager, api_client, source_file, temp_dir, snapshots_dir):
    """수정 이벤트 처리 테스트"""
    # 스냅샷 파일 생성
    snapshot_path = snapshots_dir / "test.py"
    snapshot_path.write_text("print('test')")
    
    # 스냅샷 매니저 설정
    snapshot_manager.has_changed.return_value = True
    snapshot_manager.create_snapshot.return_value = str(snapshot_path)
    
    # 이벤트 생성
    event = WatcherEvent(
        event_type="modified",
        source_path=str(source_file),
        dest_path=None,
        timestamp=datetime.now(),
        path_info=PathInfo.from_source_path(str(source_file), base_path=str(temp_dir))
    )
    
    # 학생 핸들러 생성
    student_id = "202012180"
    processor._student_handlers[student_id] = StudentEventHandler.create()
    
    # 이벤트 처리 시작
    process_task = asyncio.create_task(processor._process_student_events(student_id))
    await processor._student_handlers[student_id].queue.put(event)
    
    # 이벤트 처리 완료 대기
    await processor._student_handlers[student_id].queue.join()
    
    # API 호출 확인
    assert api_client.register_snapshot.call_count == 1
    
    # 태스크 정리
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_process_deleted_event(processor, snapshot_manager, api_client, source_file, temp_dir, snapshots_dir):
    """삭제 이벤트 처리 테스트"""
    # 스냅샷 파일 생성
    snapshot_path = snapshots_dir / "test.py"
    snapshot_path.write_text("")
    
    # 스냅샷 매니저 설정
    snapshot_manager.create_empty_snapshot.return_value = str(snapshot_path)
    
    # 이벤트 생성
    event = WatcherEvent(
        event_type="deleted",
        source_path=str(source_file),
        dest_path=None,
        timestamp=datetime.now(),
        path_info=PathInfo.from_source_path(str(source_file), base_path=str(temp_dir))
    )
    
    # 학생 핸들러 생성
    student_id = "202012180"
    processor._student_handlers[student_id] = StudentEventHandler.create()
    
    try:
        # 이벤트 처리 시작
        process_task = asyncio.create_task(processor._process_student_events(student_id))
        
        # 이벤트 추가 및 처리 완료 대기
        await processor._student_handlers[student_id].queue.put(event)
        await processor._student_handlers[student_id].queue.join()
        
        # API 호출 확인
        assert api_client.register_snapshot.call_count == 1
    finally:
        # 태스크 정리
        if not process_task.done():
            process_task.cancel()
            try:
                await process_task
            except asyncio.CancelledError:
                pass
        
        # 핸들러 정리
        if student_id in processor._student_handlers:
            await processor._student_handlers[student_id].queue.join()
            del processor._student_handlers[student_id]

@pytest.mark.asyncio
async def test_no_snapshot_if_not_changed(processor, snapshot_manager, api_client, source_file, temp_dir):
    """파일이 변경되지 않은 경우 스냅샷 생성 안 함 테스트"""
    # 스냅샷 매니저 설정
    snapshot_manager.has_changed.return_value = False
    
    # 이벤트 생성
    event = WatcherEvent(
        event_type="modified",
        source_path=str(source_file),
        dest_path=None,
        timestamp=datetime.now(),
        path_info=PathInfo.from_source_path(str(source_file), base_path=str(temp_dir))
    )
    
    # 학생 핸들러 생성
    student_id = "202012180"
    processor._student_handlers[student_id] = StudentEventHandler.create()
    
    # 이벤트 처리 시작
    process_task = asyncio.create_task(processor._process_student_events(student_id))
    await processor._student_handlers[student_id].queue.put(event)
    
    # 이벤트 처리 완료 대기
    await processor._student_handlers[student_id].queue.join()
    
    # API 호출 확인
    assert api_client.register_snapshot.call_count == 0
    
    # 태스크 정리
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_concurrent_event_processing(processor, snapshot_manager, api_client, source_dir, temp_dir, snapshots_dir):
    """동시 이벤트 처리 테스트"""
    # 스냅샷 매니저 설정
    snapshot_manager.has_changed.return_value = True
    
    # 여러 이벤트 생성
    events = []
    for i in range(3):
        # 소스 파일 생성
        source_file = source_dir / f"test{i}.py"
        source_file.write_text(f"print('test{i}')")
        
        # 스냅샷 파일 생성
        snapshot_path = snapshots_dir / f"test{i}.py"
        snapshot_path.write_text(f"print('test{i}')")
        snapshot_manager.create_snapshot.return_value = str(snapshot_path)
        
        event = WatcherEvent(
            event_type="modified",
            source_path=str(source_file),
            dest_path=None,
            timestamp=datetime.now(),
            path_info=PathInfo.from_source_path(str(source_file), base_path=str(temp_dir))
        )
        events.append(event)
    
    # 학생 핸들러 생성
    student_id = "202012180"
    processor._student_handlers[student_id] = StudentEventHandler.create()
    
    # 이벤트 처리 시작
    process_task = asyncio.create_task(processor._process_student_events(student_id))
    for event in events:
        await processor._student_handlers[student_id].queue.put(event)
    
    # 이벤트 처리 완료 대기
    await processor._student_handlers[student_id].queue.join()
    
    # API 호출 확인
    assert api_client.register_snapshot.call_count == len(events)
    
    # 태스크 정리
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass 