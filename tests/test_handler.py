import pytest
from src.core.handler import SourceCodeHandler

class TestSourceCodeHandler:
    @pytest.mark.parametrize("test_path,expected", [
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
        ("/watcher/codes/os-1-202012180/hw1/__pycache__/test.py", False),  # 캐시 디렉토리
        ("/watcher/codes/os-1-202012180/hw1/.git/test.py", False),   # 숨김 디렉토리
    ])
    def test_path_patterns(self, test_path, expected):
        """경로 패턴 테스트"""
        assert SourceCodeHandler.test_path(test_path) == expected

    @pytest.mark.parametrize("hw_number", [
        *range(1, 11)  # hw1부터 hw10까지
    ])
    def test_valid_hw_numbers(self, hw_number):
        test_path = f"/watcher/codes/os-1-202012180/hw{hw_number}/test.c"
        assert SourceCodeHandler.test_path(test_path)

    @pytest.mark.parametrize("hw_number", [
        0, 11, 12, 20, 99
    ])
    def test_invalid_hw_numbers(self, hw_number):
        test_path = f"/watcher/codes/os-1-202012180/hw{hw_number}/test.c"
        assert not SourceCodeHandler.test_path(test_path)

    @pytest.mark.parametrize("extension", [
        "c", "h", "py"
    ])
    def test_valid_extensions(self, extension):
        test_path = f"/watcher/codes/os-1-202012180/hw1/test.{extension}"
        assert SourceCodeHandler.test_path(test_path)

    @pytest.mark.parametrize("extension", [
        "cpp", "hpp", "java", "go", "js", "pyc", "pyo", "pyd"
    ])
    def test_invalid_extensions(self, extension):
        test_path = f"/watcher/codes/os-1-202012180/hw1/test.{extension}"
        assert not SourceCodeHandler.test_path(test_path) 