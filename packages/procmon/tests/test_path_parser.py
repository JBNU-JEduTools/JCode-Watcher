from pathlib import Path

import pytest
from app.path_parser import PathParser


class TestPathParser:
    """PathParser 테스트"""

    def setup_method(self):
        """Given: PathParser 인스턴스 생성"""
        self.parser = PathParser()

    def test_valid_workspace_paths(self):
        """유효한 workspace 경로 테스트"""
        test_cases = [
            ("/workspace/os-1-202012345/hw1/main.c", "hw1"),
            ("/workspace/a-2-123456789/정렬-알고리즘/test.py", "정렬-알고리즘"),
            ("/workspace/linux-10-987654321/sorting-algorithm", "sorting-algorithm"),
            ("/workspace/sys-5-111222333/과제1/project", "과제1"),
            (
                "/workspace/net-1-555666777/hw3-linked-list/src/main.c",
                "hw3-linked-list",
            ),
            ("/workspace/os-1-202012345/연결 리스트/main.c", "연결 리스트"),
        ]

        for path, expected in test_cases:
            result = self.parser.parse(path)
            assert result == expected, (
                f"Failed to parse '{path}', expected '{expected}', got '{result}'"
            )

    def test_valid_home_coder_paths(self):
        """유효한 /home/coder/project 경로 테스트"""
        test_cases = [
            ("/home/coder/project/hw1/main.c", "hw1"),
            ("/home/coder/project/정렬알고리즘/test.py", "정렬알고리즘"),
            ("/home/coder/project/sorting-algorithm", "sorting-algorithm"),
            ("/home/coder/project/과제15/subfolder/file.c", "과제15"),
        ]

        for path, expected in test_cases:
            result = self.parser.parse(path)
            assert result == expected, (
                f"Failed to parse '{path}', expected '{expected}', got '{result}'"
            )

    def test_invalid_workspace_structure(self):
        """유효하지 않은 workspace 구조 테스트"""
        invalid_paths = [
            "/workspace/hw1/main.c",  # 중간에 클래스-번호-ID 구조가 없음
            "/workspace/invalid-format/hw1/main.c",  # 잘못된 형식
            "/workspace/os/hw1/main.c",  # 번호가 없음
            "/workspace/os-1/hw1/main.c",  # ID가 없음
            "/different/path/hw1/main.c",  # workspace가 아님
        ]

        for path in invalid_paths:
            result = self.parser.parse(path)
            assert result is None, f"Should return None for invalid structure: '{path}'"

    def test_pathlib_path_input(self):
        """pathlib.Path 객체 입력 테스트"""
        path_obj = Path("/workspace/os-1-123456/과제5/main.c")
        result = self.parser.parse(path_obj)
        assert result == "과제5"

    def test_none_input_raises_exception(self):
        """None 입력 시 예외 발생 테스트"""
        with pytest.raises(ValueError, match="경로가 None입니다"):
            self.parser.parse(None)

    def test_relative_path_raises_exception(self):
        """상대 경로 입력 시 예외 발생 테스트"""
        relative_paths = [
            "hw1/main.c",
            "./hw2/test.py",
            "../workspace/os-1-123/hw3/file.c",
            "workspace/os-1-123/hw4/main.c",
        ]

        for path in relative_paths:
            with pytest.raises(ValueError, match="상대 경로 지원 안함:"):
                self.parser.parse(path)

    def test_escape_characters_raise_exception(self):
        """이스케이프 문자 포함 시 예외 발생 테스트"""
        paths_with_escapes = [
            "/workspace/os-1-123/hw1/main.c\n",
            "/workspace/os-1-123/hw1/main.c\t",
            "/workspace/os-1-123/hw1/main.c\r",
        ]

        for path in paths_with_escapes:
            with pytest.raises(ValueError, match="경로에 이스케이프 문자 포함:"):
                self.parser.parse(path)

    def test_path_normalization(self):
        """경로 정규화 테스트"""
        normalized_cases = [
            ("/workspace/os-1-123//hw1//main.c", "hw1"),
            ("/workspace/os-1-123/./hw2/main.c", "hw2"),
            ("/workspace/os-1-123/subdir/../과제3/main.c", "과제3"),
        ]

        for path, expected in normalized_cases:
            result = self.parser.parse(path)
            assert result == expected, f"Failed to handle normalized path '{path}'"

    def test_various_directory_names(self):
        """다양한 과제 디렉토리명 테스트"""
        test_cases = [
            ("/workspace/os-1-123/hw1", "hw1"),
            ("/workspace/os-1-123/과제2/", "과제2"),
            ("/workspace/os-1-123/sorting-algorithm/main.c", "sorting-algorithm"),
            ("/workspace/os-1-123/이진-트리/test.py", "이진-트리"),
            ("/workspace/os-1-123/hw5-linked-list/app.js", "hw5-linked-list"),
        ]

        for path, expected in test_cases:
            result = self.parser.parse(path)
            assert result == expected, f"Failed to parse '{path}'"

    def test_hidden_directory_rejected(self):
        """숨김 디렉토리가 거부되는지 테스트"""
        hidden_paths = [
            "/workspace/os-1-123/.hidden/main.c",
            "/home/coder/project/.git/config",
        ]

        for path in hidden_paths:
            result = self.parser.parse(path)
            assert result is None, f"Should return None for hidden directory: '{path}'"

    def test_alphanumeric_subject_codes(self):
        """영숫자 조합 과목코드 테스트"""
        test_cases = [
            ("/workspace/test252-2-202012180/과제1/hihihi.c", "과제1"),
            ("/workspace/cs101-1-202012345/hw2/main.c", "hw2"),
            ("/workspace/OS2023-1-202011111/정렬/kernel.c", "정렬"),
        ]

        for path, expected in test_cases:
            result = self.parser.parse(path)
            assert result == expected, (
                f"Failed to parse alphanumeric subject code '{path}'"
            )

    def test_empty_and_whitespace_paths(self):
        """빈 문자열과 공백 경로 테스트"""
        relative_path_cases = ["", "   "]
        for path in relative_path_cases:
            with pytest.raises(ValueError, match="상대 경로 지원 안함:"):
                self.parser.parse(path)

        root_paths = ["/", "//"]
        for path in root_paths:
            result = self.parser.parse(path)
            assert result is None, f"Should return None for root path: '{path}'"

    def test_assignment_id_requires_immutable_directory(self):
        assert self.parser.assignment_id("assignment-42") == 42
        with pytest.raises(ValueError, match="불변 식별자"):
            self.parser.assignment_id("hw1")


if __name__ == "__main__":
    pytest.main([__file__])
