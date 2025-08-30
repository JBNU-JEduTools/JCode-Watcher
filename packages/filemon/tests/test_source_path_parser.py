import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from app.source_path_parser import SourcePathParser


@pytest.fixture
def parser():
    """SourcePathParser 인스턴스"""
    return SourcePathParser()


@pytest.fixture
def mock_settings():
    """Mock settings"""
    mock = Mock()
    mock.WATCH_ROOT = Path("/watch/root")
    return mock


class TestSourcePathParser:
    """SourcePathParser 테스트"""

    @patch('app.source_path_parser.settings')
    def test_parse_success_simple_path(self, mock_settings, parser):
        """정상 경로 파싱 테스트 - 단순 구조"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-1-202012345/hw1/test.c")
        
        # When
        result = parser.parse(target_path)
        
        # Then
        expected = {
            'class_div': 'os-1',
            'hw_name': 'hw1', 
            'student_id': '202012345',
            'filename': 'test.c'
        }
        assert result == expected

    @patch('app.source_path_parser.settings')
    def test_parse_success_nested_path(self, mock_settings, parser):
        """정상 경로 파싱 테스트 - 중첩 구조"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/java-2-202098765/hw2/src/main/Main.java")
        
        # When
        result = parser.parse(target_path)
        
        # Then
        expected = {
            'class_div': 'java-2',
            'hw_name': 'hw2',
            'student_id': '202098765', 
            'filename': 'src@main@Main.java'  # @ 구분자로 결합
        }
        assert result == expected

    @patch('app.source_path_parser.settings')
    def test_parse_success_deep_nested_path(self, mock_settings, parser):
        """정상 경로 파싱 테스트 - 깊은 중첩 구조"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/python-3-202011111/project1/lib/utils/helper.py")
        
        # When
        result = parser.parse(target_path)
        
        # Then
        expected = {
            'class_div': 'python-3',
            'hw_name': 'project1',
            'student_id': '202011111',
            'filename': 'lib@utils@helper.py'
        }
        assert result == expected

    @patch('app.source_path_parser.settings')
    def test_parse_path_not_under_watch_root(self, mock_settings, parser):
        """WATCH_ROOT 하위가 아닌 경로"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/other/path/os-1-202012345/hw1/test.c")
        
        # When & Then
        with pytest.raises(ValueError, match="파일 경로가 WATCH_ROOT 하위에 있지 않음"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_insufficient_path_parts(self, mock_settings, parser):
        """경로 구성요소 부족"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-1-202012345/hw1")  # 파일명 없음
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 경로 구조"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_insufficient_path_parts_too_short(self, mock_settings, parser):
        """경로가 너무 짧음"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-1-202012345")  # hw_name, filename 없음
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 경로 구조"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_invalid_directory_format_too_few_parts(self, mock_settings, parser):
        """디렉토리 형식 오류 - 구성요소 부족"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-202012345/hw1/test.c")  # 분반 정보 없음
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_invalid_directory_format_too_many_parts(self, mock_settings, parser):
        """디렉토리 형식 오류 - 구성요소 과다"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-1-extra-202012345/hw1/test.c")  # 불필요한 구성요소
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_empty_directory_name(self, mock_settings, parser):
        """빈 디렉토리명"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/--/hw1/test.c")  # 빈 과목명과 분반
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_special_characters_in_filename(self, mock_settings, parser):
        """파일명에 특수문자 포함"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/cpp-1-202012345/hw1/test@file#1.cpp")
        
        # When
        result = parser.parse(target_path)
        
        # Then
        expected = {
            'class_div': 'cpp-1',
            'hw_name': 'hw1',
            'student_id': '202012345',
            'filename': 'test@file#1.cpp'
        }
        assert result == expected

    @patch('app.source_path_parser.settings')
    def test_parse_unicode_characters(self, mock_settings, parser):
        """유니코드 문자 처리"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/한글-1-202012345/과제1/테스트.py")
        
        # When
        result = parser.parse(target_path)
        
        # Then
        expected = {
            'class_div': '한글-1',
            'hw_name': '과제1',
            'student_id': '202012345',
            'filename': '테스트.py'
        }
        assert result == expected

    @patch('app.source_path_parser.settings')
    def test_parse_subject_with_hyphen_should_fail(self, mock_settings, parser):
        """과목명에 하이픈이 포함된 경우 (리젝되어야 함)"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/data-structure-1-202012345/hw1/test.c")
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_student_id_with_hyphen_should_fail(self, mock_settings, parser):
        """학번에 하이픈이 포함된 경우 (리젝되어야 함)"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-1-2020-12345/hw1/test.c")
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_class_division_with_hyphen_should_fail(self, mock_settings, parser):
        """분반에 하이픈이 포함된 경우 (리젝되어야 함)"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/os-1-a-202012345/hw1/test.c")
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)

    @patch('app.source_path_parser.settings')
    def test_parse_multiple_hyphens_should_fail(self, mock_settings, parser):
        """여러 하이픈이 연속으로 포함된 경우 (리젝되어야 함)"""
        # Given
        mock_settings.WATCH_ROOT = Path("/watch/root")
        target_path = Path("/watch/root/computer-science-advanced-1-202012345/hw1/test.c")
        
        # When & Then
        with pytest.raises(ValueError, match="잘못된 디렉토리 형식"):
            parser.parse(target_path)