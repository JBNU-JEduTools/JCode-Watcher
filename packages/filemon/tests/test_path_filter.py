import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.path_filter import PathFilter


class TestPathFilterPatterns:
    """PathFilter 패턴 매칭 테스트"""

    @pytest.mark.parametrize("file_path,expected", [
        # 유효한 경로들
        ("/watcher/codes/class-1-202012345/hw1/test.c", True),
        ("/watcher/codes/class-1-202012345/hw1/main.h", True),
        ("/watcher/codes/os-2-202112345/hw5/src/test.py", True),
        ("/watcher/codes/ds-4-202312345/hw2/a/b/main.hpp", True),
        ("/watcher/codes/class-1-202012345/hw0/test.c", True),  # hw0는 허용됨
        ("/watcher/codes/algo-1-202012345/hw10/util.cpp", True),  # hw10은 허용됨
        
        # 무효한 경로들 - 무시 패턴에 걸림
        ("/watcher/codes/algo-3-202212345/hw10/lib/util.cpp", False),  # lib 디렉토리는 무시됨
        ("/watcher/codes/class-1-202012345/hw1/.env/test.c", False),  # .env 디렉토리
        ("/watcher/codes/class-1-202012345/hw1/ENV/test.c", False),  # ENV 디렉토리
        ("/watcher/codes/class-1-202012345/hw1/site-packages/test.c", False),  # site-packages
        ("/watcher/codes/class-1-202012345/hw1/dist-packages/test.c", False),  # dist-packages
        ("/watcher/codes/class-1-202012345/hw1/lib64/test.c", False),  # lib64
        ("/watcher/codes/class-1-202012345/hw1/libs/test.c", False),  # libs
        ("/watcher/codes/class-1-202012345/hw1/.hidden/test.c", False),  # 숨김 디렉토리
        ("/watcher/codes/class-1-202012345/hw1/.git/test.c", False),  # .git 디렉토리
        
        # 무효한 경로들 - 잘못된 hw 번호  
        ("/watcher/codes/class-1-202012345/hw11/test.c", False),
        ("/watcher/codes/class-1-202012345/hw99/test.c", False),
        
        # 무효한 경로들 - 잘못된 확장자
        ("/watcher/codes/class-1-202012345/hw1/test.txt", False),
        ("/watcher/codes/class-1-202012345/hw1/test.java", False),
        ("/watcher/codes/class-1-202012345/hw1/test.js", False),
        
        # 무효한 경로들 - 잘못된 구조
        ("/watcher/codes/hw1/test.c", False),  # class-div-student_id 누락
        ("/watcher/codes/class-1/hw1/test.c", False),  # student_id 누락
        ("/watcher/codes/class-1-202012345/test.c", False),  # hw 디렉토리 누락
    ])
    def test_should_process_path_patterns(self, file_path, expected):
        """경로 패턴 매칭 테스트"""
        path_filter = PathFilter()
        result = path_filter.should_process_path(file_path)
        assert result == expected

    @pytest.mark.parametrize("hw_number", [
        *range(0, 11)  # hw0부터 hw10까지
    ])
    def test_valid_hw_numbers(self, hw_number):
        """유효한 hw 번호 테스트"""
        path_filter = PathFilter()
        file_path = f"/watcher/codes/class-1-202012345/hw{hw_number}/test.c"
        assert path_filter.should_process_path(file_path) is True

    @pytest.mark.parametrize("hw_number", [
        11, 12, 20, 99
    ])
    def test_invalid_hw_numbers(self, hw_number):
        """무효한 hw 번호 테스트"""
        path_filter = PathFilter()
        file_path = f"/watcher/codes/class-1-202012345/hw{hw_number}/test.c"
        assert path_filter.should_process_path(file_path) is False

    @pytest.mark.parametrize("extension", [
        "c", "h", "py", "cpp", "hpp"
    ])
    def test_valid_extensions(self, extension):
        """유효한 파일 확장자 테스트"""
        path_filter = PathFilter()
        file_path = f"/watcher/codes/class-1-202012345/hw1/test.{extension}"
        assert path_filter.should_process_path(file_path) is True

    @pytest.mark.parametrize("extension", [
        "java", "go", "js", "pyc", "pyo", "pyd", "txt", "md", "json"
    ])
    def test_invalid_extensions(self, extension):
        """무효한 파일 확장자 테스트"""
        path_filter = PathFilter()
        file_path = f"/watcher/codes/class-1-202012345/hw1/test.{extension}"
        assert path_filter.should_process_path(file_path) is False

    @pytest.mark.parametrize("class_pattern", [
        "class-1-202012345",  # 기본 형태
        "os-2-202112345",     # 다른 과목
        "algo-3-202212345",   # 알고리즘
        "ds-4-202312345",     # 자료구조
    ])
    def test_valid_class_patterns(self, class_pattern):
        """유효한 클래스 패턴 테스트"""
        path_filter = PathFilter()
        file_path = f"/watcher/codes/{class_pattern}/hw1/test.c"
        assert path_filter.should_process_path(file_path) is True

    @pytest.mark.parametrize("invalid_pattern", [
        "class-1",           # student_id 누락
        "202012345",         # class-div 누락  
        "class-202012345",   # div 누락
        "class",             # div와 student_id 모두 누락
    ])
    def test_invalid_class_patterns(self, invalid_pattern):
        """무효한 클래스 패턴 테스트"""
        path_filter = PathFilter()
        file_path = f"/watcher/codes/{invalid_pattern}/hw1/test.c"
        assert path_filter.should_process_path(file_path) is False


class TestPathFilterFileHandling:
    """PathFilter 파일 처리 테스트"""

    def test_should_process_file_with_regular_file(self):
        """일반 파일에 대한 처리 테스트"""
        path_filter = PathFilter()
        
        with patch('app.path_filter.os.path.isdir', return_value=False):
            with patch.object(path_filter, 'should_process_path', return_value=True) as mock_process_path:
                result = path_filter.should_process_file("/watcher/codes/class-1-202012345/hw1/test.c")
                
                assert result is True
                mock_process_path.assert_called_once_with("/watcher/codes/class-1-202012345/hw1/test.c")

    def test_should_process_file_with_directory(self):
        """디렉토리에 대한 처리 테스트 (무시되어야 함)"""
        path_filter = PathFilter()
        
        with patch('app.path_filter.os.path.isdir', return_value=True):
            result = path_filter.should_process_file("/watcher/codes/class-1-202012345/hw1")
            
            assert result is False

    def test_should_process_file_with_invalid_path(self):
        """무효한 경로에 대한 처리 테스트"""
        path_filter = PathFilter()
        
        with patch('app.path_filter.os.path.isdir', return_value=False):
            with patch.object(path_filter, 'should_process_path', return_value=False) as mock_process_path:
                result = path_filter.should_process_file("/invalid/path/test.txt")
                
                assert result is False
                mock_process_path.assert_called_once_with("/invalid/path/test.txt")


class TestPathFilterDepthLimits:
    """PathFilter 디렉토리 깊이 제한 테스트"""

    @pytest.mark.parametrize("depth_path,expected", [
        # 허용되는 깊이들
        ("/watcher/codes/class-1-202012345/hw1/test.c", True),           # 0 depth
        ("/watcher/codes/class-1-202012345/hw1/dir1/test.c", True),      # 1 depth
        ("/watcher/codes/class-1-202012345/hw1/dir1/dir2/test.c", True), # 2 depth
        ("/watcher/codes/class-1-202012345/hw1/a/b/c/test.c", True),     # 3 depth
        ("/watcher/codes/class-1-202012345/hw1/a/b/c/d/test.c", True),   # 4 depth
    ])
    def test_directory_depth_limits(self, depth_path, expected):
        """디렉토리 깊이 제한 테스트"""
        path_filter = PathFilter()
        result = path_filter.should_process_path(depth_path)
        assert result == expected


class TestPathFilterIgnorePatterns:
    """PathFilter 무시 패턴 테스트"""

    @pytest.mark.parametrize("ignore_path", [
        # 환경 디렉토리들
        "/watcher/codes/class-1-202012345/hw1/.env/config.py",
        "/watcher/codes/class-1-202012345/hw1/env/settings.py",
        "/watcher/codes/class-1-202012345/hw1/ENV/vars.py",
        
        # 패키지 디렉토리들
        "/watcher/codes/class-1-202012345/hw1/site-packages/module.py",
        "/watcher/codes/class-1-202012345/hw1/dist-packages/package.py",
        
        # 라이브러리 디렉토리들
        "/watcher/codes/class-1-202012345/hw1/lib/library.c",
        "/watcher/codes/class-1-202012345/hw1/lib64/lib64.c",
        "/watcher/codes/class-1-202012345/hw1/libs/libs.c",
        
        # 숨김 파일/디렉토리들
        "/watcher/codes/class-1-202012345/hw1/.git/config",
        "/watcher/codes/class-1-202012345/hw1/.vscode/settings.json",
        "/watcher/codes/class-1-202012345/hw1/.hidden/file.py",
        "/watcher/codes/class-1-202012345/hw1/.DS_Store",
    ])
    def test_ignore_patterns_comprehensive(self, ignore_path):
        """포괄적인 무시 패턴 테스트"""
        path_filter = PathFilter()
        result = path_filter.should_process_path(ignore_path)
        assert result is False


class TestPathFilterInitialization:
    """PathFilter 초기화 테스트"""

    @patch('app.path_filter.settings')
    def test_initialization_with_settings(self, mock_settings):
        """설정을 통한 초기화 테스트"""
        mock_settings.WATCH_ROOT = Path('/test/watch/root')
        
        path_filter = PathFilter()
        
        assert path_filter.base_path == '/test/watch/root'
        assert '/test/watch/root' in path_filter.source_pattern

    def test_pattern_compilation(self):
        """패턴 컴파일 테스트"""
        path_filter = PathFilter()
        
        # 패턴이 올바르게 포맷되었는지 확인
        assert path_filter.base_path in path_filter.source_pattern
        assert 'hw(?:[0-9]|10)' in path_filter.source_pattern
        assert '\\.(c|h|py|cpp|hpp)$' in path_filter.source_pattern


class TestPathFilterEdgeCases:
    """PathFilter 엣지 케이스 테스트"""

    def test_empty_path(self):
        """빈 경로 테스트"""
        path_filter = PathFilter()
        result = path_filter.should_process_path("")
        assert result is False

    def test_root_path(self):
        """루트 경로 테스트"""
        path_filter = PathFilter()
        result = path_filter.should_process_path("/")
        assert result is False

    def test_relative_path(self):
        """상대 경로 테스트"""
        path_filter = PathFilter()
        result = path_filter.should_process_path("./test/file.c")
        assert result is False

    def test_path_with_spaces(self):
        """공백이 포함된 경로 테스트"""
        path_filter = PathFilter()
        # 공백이 있는 경로는 패턴에 맞지 않으므로 False
        result = path_filter.should_process_path("/watcher/codes/class 1-202012345/hw1/test.c")
        assert result is False

    def test_case_sensitivity(self):
        """대소문자 구분 테스트"""
        path_filter = PathFilter()
        # 대문자 확장자는 허용되지 않음
        result = path_filter.should_process_path("/watcher/codes/class-1-202012345/hw1/test.C")
        assert result is False