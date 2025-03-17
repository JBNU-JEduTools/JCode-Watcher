import pytest
from pathlib import Path
from src.core.path_info import PathInfo

def test_from_source_path_basic():
    """기본적인 경로 파싱 테스트"""
    source_path = "/watcher/codes/os-1-202012180/hw1/hello.c"
    path_info = PathInfo.from_source_path(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "hello.c"
    assert path_info.source_path == Path(source_path)

def test_from_source_path_nested():
    """중첩 경로 파싱 테스트"""
    source_path = "/watcher/codes/os-1-202012180/hw1/depth1/depth2/test.py"
    path_info = PathInfo.from_source_path(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "depth1@depth2@test.py"

def test_from_source_path_invalid_format():
    """잘못된 경로 형식 테스트"""
    with pytest.raises(ValueError):
        PathInfo.from_source_path("/watcher/codes/invalid-path/hw1/test.py")

def test_get_snapshot_dir():
    """스냅샷 디렉토리 경로 생성 테스트"""
    path_info = PathInfo.from_source_path(
        "/watcher/codes/os-1-202012180/hw1/depth1/depth2/test.py"
    )
    snapshot_dir = path_info.get_snapshot_dir("/watcher/snapshots")
    
    assert snapshot_dir == Path(
        "/watcher/snapshots/os-1/hw1/202012180/depth1@depth2@test.py"
    )

def test_get_snapshot_path():
    """스냅샷 파일 경로 생성 테스트"""
    path_info = PathInfo.from_source_path(
        "/watcher/codes/os-1-202012180/hw1/depth1/depth2/test.py"
    )
    snapshot_path = path_info.get_snapshot_path(
        "/watcher/snapshots", 
        "20240316_123456"
    )
    
    assert snapshot_path == Path(
        "/watcher/snapshots/os-1/hw1/202012180/depth1@depth2@test.py/20240316_123456.py"
    )

def test_nested_path_with_same_hw_name():
    """과제 이름과 같은 하위 디렉토리가 있는 경우 테스트"""
    path_info = PathInfo.from_source_path(
        "/watcher/codes/os-1-202012180/hw2/hw1/test.c"
    )
    snapshot_dir = path_info.get_snapshot_dir("/watcher/snapshots")
    
    assert snapshot_dir == Path(
        "/watcher/snapshots/os-1/hw2/202012180/hw1@test.c"
    )

def test_get_snapshot_path_uses_snapshot_dir():
    """get_snapshot_path가 get_snapshot_dir를 사용하는지 테스트"""
    path_info = PathInfo.from_source_path(
        "/watcher/codes/os-1-202012180/hw1/test.c"
    )
    snapshot_dir = path_info.get_snapshot_dir("/watcher/snapshots")
    snapshot_path = path_info.get_snapshot_path(
        "/watcher/snapshots", 
        "20240316_123456"
    )
    
    assert snapshot_path == snapshot_dir / "20240316_123456.c"

def test_from_source_path_with_custom_base():
    """커스텀 base_path를 사용한 경로 파싱 테스트"""
    source_path = "/custom/base/os-1-202012180/hw1/test.c"
    path_info = PathInfo.from_source_path(source_path, base_path="/custom/base")
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "test.c"
    assert path_info.source_path == Path(source_path)

def test_from_source_path_with_invalid_class_format():
    """잘못된 과목-분반 형식 테스트"""
    with pytest.raises(ValueError):
        PathInfo.from_source_path("/watcher/codes/invalid-format/hw1/test.c")

def test_from_source_path_with_path_object():
    """Path 객체를 사용한 경로 파싱 테스트"""
    source_path = Path("/watcher/codes/os-1-202012180/hw1/test.c")
    path_info = PathInfo.from_source_path(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "test.c"
    assert path_info.source_path == source_path

def test_get_snapshot_path_with_different_extension():
    """다른 확장자를 가진 파일의 스냅샷 경로 생성 테스트"""
    path_info = PathInfo.from_source_path(
        "/watcher/codes/os-1-202012180/hw1/test.py"
    )
    snapshot_path = path_info.get_snapshot_path(
        "/watcher/snapshots", 
        "20240316_123456"
    )
    
    assert snapshot_path == Path(
        "/watcher/snapshots/os-1/hw1/202012180/test.py/20240316_123456.py"
    )

def test_get_snapshot_dir_with_absolute_path():
    """절대 경로를 사용한 스냅샷 디렉토리 생성 테스트"""
    path_info = PathInfo.from_source_path(
        "/watcher/codes/os-1-202012180/hw1/test.c"
    )
    snapshot_dir = path_info.get_snapshot_dir("/absolute/path/snapshots")
    
    assert snapshot_dir == Path(
        "/absolute/path/snapshots/os-1/hw1/202012180/test.c"
    )

def test_from_source_path_with_special_characters():
    """특수 문자가 포함된 경로 파싱 테스트"""
    source_path = "/watcher/codes/os-1-202012180/hw1/test-file_1.c"
    path_info = PathInfo.from_source_path(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "test-file_1.c"
    assert path_info.source_path == Path(source_path) 