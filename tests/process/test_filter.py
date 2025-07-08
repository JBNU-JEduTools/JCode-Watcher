import pytest
from unittest.mock import Mock, patch
from src.process.filter import ProcessFilter
from src.process.types import ProcessType
from src.homework.checker import HomeworkChecker

class TestProcessFilter:
    @pytest.fixture
    def mock_settings(self):
        """테스트용 설정 모의 객체"""
        with patch('src.process.filter.settings') as mock_settings:
            # 테스트용 프로세스 패턴 설정
            mock_settings.PROCESS_PATTERNS = {
                'GCC': ['/usr/bin/gcc'],
                'CLANG': ['/usr/bin/clang'],
                'GPP': ['/usr/bin/g++'],
                'PYTHON': ['/usr/bin/python3']
            }
            yield mock_settings

    @pytest.fixture
    def mock_homework_checker(self):
        """테스트용 HomeworkChecker 모의 객체"""
        checker = Mock(spec=HomeworkChecker)
        
        def get_homework_info(path: str) -> str:
            if '/os-5-202012180/hw1/' in path:
                return 'hw1'
            if '/network-1-201912345/hw2/' in path:
                return 'hw2'
            return None
            
        checker.get_homework_info.side_effect = get_homework_info
        return checker

    @pytest.fixture
    def process_filter(self, mock_settings, mock_homework_checker):
        """테스트용 ProcessFilter 인스턴스"""
        return ProcessFilter(mock_homework_checker)

    def test_system_binary_detection(self, process_filter):
        """시스템 바이너리 감지 테스트"""
        test_cases = [
            ('/usr/bin/gcc', ProcessType.GCC),
            ('/usr/bin/clang', ProcessType.CLANG),
            ('/usr/bin/g++', ProcessType.GPP),
            ('/usr/bin/python3', ProcessType.PYTHON),
            ('/usr/bin/unknown', ProcessType.UNKNOWN)
        ]
        
        for binary_path, expected_type in test_cases:
            result = process_filter.get_process_type(binary_path)
            assert result == expected_type, f"Failed for binary: {binary_path}"

    def test_homework_binary_detection(self, process_filter):
        """과제 실행 파일 감지 테스트"""
        test_cases = [
            ('/os-5-202012180/hw1/main', ProcessType.USER_BINARY),
            ('/os-5-202012180/hw1/test/program', ProcessType.USER_BINARY),
            ('/network-1-201912345/hw2/main', ProcessType.USER_BINARY),
            ('/invalid-path/hw1/main', ProcessType.UNKNOWN),
            ('/os-5-202012180/invalid/main', ProcessType.UNKNOWN)
        ]
        
        for binary_path, expected_type in test_cases:
            result = process_filter.get_process_type(binary_path)
            assert result == expected_type, f"Failed for binary: {binary_path}"

    def test_error_handling(self, process_filter, mock_homework_checker):
        """에러 처리 테스트"""
        # HomeworkChecker가 예외를 발생시키는 경우
        mock_homework_checker.get_homework_info.side_effect = Exception("Test error")
        
        result = process_filter.get_process_type('/os-5-202012180/hw1/main')
        assert result == ProcessType.UNKNOWN

    def test_edge_cases(self, process_filter):
        """엣지 케이스 테스트"""
        test_cases = [
            ('', ProcessType.UNKNOWN),
            ('/', ProcessType.UNKNOWN),
            (None, ProcessType.UNKNOWN),
            ('/usr/bin/', ProcessType.UNKNOWN),
            ('/os-5-202012180/hw1', ProcessType.UNKNOWN)  # 디렉토리만 있는 경우
        ]
        
        for binary_path, expected_type in test_cases:
            result = process_filter.get_process_type(binary_path)
            assert result == expected_type, f"Failed for binary: {binary_path}"

    def test_multiple_patterns_same_binary(self, process_filter):
        """동일한 바이너리에 대한 여러 패턴 테스트"""
        # gcc-12와 gcc가 모두 매칭되는 경우
        binary_path = '/usr/bin/gcc-12'
        with patch('src.process.filter.settings.PROCESS_PATTERNS', {
            'GCC': ['/usr/bin/gcc', '/usr/bin/gcc-12'],
            'CLANG': ['/usr/bin/clang']
        }):
            result = process_filter.get_process_type(binary_path)
            assert result == ProcessType.GCC 