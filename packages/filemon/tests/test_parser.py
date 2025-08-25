import pytest
from pathlib import Path
from unittest.mock import MagicMock
from app.parser import SourceFileParser

@pytest.fixture(autouse=True)
def mock_settings(mocker):
    """모든 테스트에 대해 자동으로 settings 모듈을 모킹합니다."""
    settings = MagicMock()
    settings.BASE_PATH = Path('/watcher/codes')
    settings.SNAPSHOT_BASE = Path('/watcher/snapshots')
    mocker.patch('app.parser.settings', settings)

@pytest.fixture
def parser():
    """SourceFileParser 인스턴스를 반환하는 pytest ਫਿਕਸਚਰ"""
    return SourceFileParser()

def test_parse_basic(parser):
    """기본적인 경로 파싱 테스트"""
    source_path = "/watcher/codes/os-1-202012180/hw1/hello.c"
    path_info = parser.parse(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "hello.c"
    assert path_info.source_path == Path(source_path)

def test_parse_nested(parser):
    """중첩 경로 파싱 테스트"""
    source_path = "/watcher/codes/os-1-202012180/hw1/depth1/depth2/test.py"
    path_info = parser.parse(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "depth1@depth2@test.py"

def test_parse_invalid_format(parser):
    """잘못된 경로 형식 테스트"""
    with pytest.raises(ValueError):
        parser.parse("/watcher/codes/invalid-path/hw1/test.py")

def test_get_snapshot_dir(parser):
    """스냅샷 디렉토리 경로 생성 테스트"""
    path_info = parser.parse(
        "/watcher/codes/os-1-202012180/hw1/depth1/depth2/test.py"
    )
    snapshot_dir = parser.get_snapshot_dir(path_info)
    
    assert snapshot_dir == Path(
        "/watcher/snapshots/os-1/hw1/202012180/depth1@depth2@test.py"
    )

def test_get_snapshot_path(parser):
    """스냅샷 파일 경로 생성 테스트"""
    path_info = parser.parse(
        "/watcher/codes/os-1-202012180/hw1/depth1/depth2/test.py"
    )
    snapshot_path = parser.get_snapshot_path(path_info, "20240316_123456")
    
    assert snapshot_path == Path(
        "/watcher/snapshots/os-1/hw1/202012180/depth1@depth2@test.py/20240316_123456.py"
    )

def test_nested_path_with_same_hw_name(parser):
    """과제 이름과 같은 하위 디렉토리가 있는 경우 테스트"""
    path_info = parser.parse(
        "/watcher/codes/os-1-202012180/hw2/hw1/test.c"
    )
    snapshot_dir = parser.get_snapshot_dir(path_info)
    
    assert snapshot_dir == Path(
        "/watcher/snapshots/os-1/hw2/202012180/hw1@test.c"
    )

def test_get_snapshot_path_uses_snapshot_dir(parser):
    """get_snapshot_path가 get_snapshot_dir를 사용하는지 테스트"""
    path_info = parser.parse(
        "/watcher/codes/os-1-202012180/hw1/test.c"
    )
    snapshot_dir = parser.get_snapshot_dir(path_info)
    snapshot_path = parser.get_snapshot_path(path_info, "20240316_123456")
    
    assert snapshot_path == snapshot_dir / "20240316_123456.c"

def test_parse_with_invalid_class_format(parser):
    """잘못된 과목-분반 형식 테스트"""
    with pytest.raises(ValueError):
        parser.parse("/watcher/codes/invalid-format/hw1/test.c")

def test_parse_with_path_object(parser):
    """Path 객체를 사용한 경로 파싱 테스트"""
    source_path = Path("/watcher/codes/os-1-202012180/hw1/test.c")
    path_info = parser.parse(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "test.c"
    assert path_info.source_path == source_path

def test_get_snapshot_path_with_different_extension(parser):
    """다른 확장자를 가진 파일의 스냅샷 경로 생성 테스트"""
    path_info = parser.parse(
        "/watcher/codes/os-1-202012180/hw1/test.py"
    )
    snapshot_path = parser.get_snapshot_path(path_info, "20240316_123456")
    
    assert snapshot_path == Path(
        "/watcher/snapshots/os-1/hw1/202012180/test.py/20240316_123456.py"
    )

def test_parse_with_special_characters(parser):
    """특수 문자가 포함된 경로 파싱 테스트"""
    source_path = "/watcher/codes/os-1-202012180/hw1/test-file_1.c"
    path_info = parser.parse(source_path)
    
    assert path_info.class_div == "os-1"
    assert path_info.student_id == "202012180"
    assert path_info.hw_name == "hw1"
    assert path_info.filename == "test-file_1.c"
    assert path_info.source_path == Path(source_path)