import pytest
import re
from src.core.watchdog_handler import SourceCodeHandler
from src.config.settings import SOURCE_PATTERNS, IGNORE_PATTERNS

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

class TestSourceCodeHandler:
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