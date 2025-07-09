import pytest
from pathlib import Path
from src.homework.checker import HomeworkChecker

class TestHomeworkChecker:
    @pytest.fixture
    def checker(self):
        """테스트용 HomeworkChecker 인스턴스"""
        return HomeworkChecker()

    def test_valid_homework_paths(self, checker):
        """유효한 과제 경로 테스트"""
        test_cases = [
            # 1. 학생 볼륨 기본 케이스
            ("/workspace/os-5-202012180/hw1/main.c", "hw1"),
            ("/workspace/network-1-201912345/hw20/test", "hw20"),
            
            # 2. 과제 번호 엣지 케이스
            ("/workspace/os-1-202012345/hw1/test", "hw1"),     # 최소값
            ("/workspace/os-1-202012345/hw20/test", "hw20"),   # 최대값
            
            # 3. 분반 번호 엣지 케이스
            ("/workspace/os-1-202012345/hw1/main", "hw1"),     # 최소 분반
            ("/workspace/os-99-202012345/hw1/main", "hw1"),    # 최대 분반
            
            # 4. 학번 엣지 케이스
            ("/workspace/os-1-1/hw1/test", "hw1"),             # 한 자리 학번
            ("/workspace/os-1-123456789012/hw1/main", "hw1"),  # 12자리 학번
            
            # 5. 과목명 다양성
            ("/workspace/os-1-202012345/hw1/main", "hw1"),
            ("/workspace/network-1-202012345/hw1/main", "hw1"),
            ("/workspace/system-1-202012345/hw1/main", "hw1"),
            ("/workspace/algorithm-1-202012345/hw1/main", "hw1"),
            ("/workspace/database-1-202012345/hw1/main", "hw1"),
            
            # 6. 프로젝트 경로 케이스
            ("/home/coder/project/hw1/main.c", "hw1"),
            ("/home/coder/project/hw1/src/main.c", "hw1"),
            ("/home/coder/project/hw20/test/main", "hw20"),
            
            # 7. 특수한 경로 구조
            ("/workspace/os-1-202012345/hw1/src/test/main", "hw1"),  # 깊은 중첩
            ("/workspace/os-1-202012345/hw1/", "hw1"),               # 끝에 슬래시
            ("/workspace/os-1-202012345/hw1", "hw1"),                # 디렉토리만
            
            # 8. Python 스크립트 경로
            ("/workspace/os-1-202012345/hw1/solution.py", "hw1"),     # 기본 Python 파일
            ("/home/coder/project/hw2/test.py", "hw2"),     # 프로젝트의 Python 파일
        ]
        
        for path, expected_hw_dir in test_cases:
            result = checker.get_homework_info(path)
            assert result == expected_hw_dir, \
                f"Failed for path: {path}\nExpected: {expected_hw_dir}\nGot: {result}"

    def test_invalid_format_paths(self, checker):
        """잘못된 형식의 경로 테스트"""
        invalid_paths = [
            # 1. 과목-분반-학번 형식 오류
            "/workspace/OS-5-202012180/hw1/main.c",      # 대문자 과목명
            "/workspace/os5-1-202012180/hw1/main",       # 과목명 형식 오류
            "/workspace/os-a-202012180/hw1/main.c",      # 분반이 숫자가 아님
            "/workspace/os--1-202012180/hw1/main",       # 잘못된 분반 구분자
            "/workspace/os-1-abc/hw1",                    # 학번이 숫자가 아님
            
            # 2. 과제 디렉토리 형식 오류
            "/workspace/os-1-202012345/homework1",        # 잘못된 과제 디렉토리 형식
            "/workspace/os-1-202012345/hwx/main",        # 과제 번호가 숫자가 아님
            
            # 3. 경로 구조 오류
            "relative/path/hw1/main.c",                  # 상대 경로
            "/project/hw1/main.c",                       # 잘못된 경로 구조
            "/workspace/os-1-202012345/hw1/../main",     # 상위 디렉토리 참조
            "~/workspace/os-1-202012180/hw1",            # 상대경로(~)
        ]
        
        for path in invalid_paths:
            result = checker.get_homework_info(path)
            assert result is None, \
                f"Expected None for invalid format path: {path}\nGot: {result}"

    def test_invalid_value_ranges(self, checker):
        """유효하지 않은 값 범위 테스트"""
        invalid_paths = [
            # 과제 번호 범위만 체크 (분반 번호는 모든 양의 정수 허용)
            "/workspace/os-1-202012345/hw0/main",      # hw0 (불가)
            "/workspace/os-1-202012345/hw21/main",     # hw21 (불가)
            "/workspace/os-1-202012345/hw99/main",     # hw99 (불가)
            "/home/coder/project/hw0/main",   # hw0 (불가)
            "/home/coder/project/hw21/main",  # hw21 (불가)
        ]
        
        for path in invalid_paths:
            result = checker.get_homework_info(path)
            assert result is None, \
                f"Expected None for invalid range path: {path}\nGot: {result}"

    def test_nested_homework_paths(self, checker):
        """중첩된 과제 디렉토리 테스트"""
        nested_paths = [
            # 1. 과제 디렉토리 중첩
            "/workspace/os-5-202012180/hw1/hw2/main.c",       # hw1 안의 hw2
            "/workspace/network-1-201912345/hw1/test/hw3",     # hw1 안의 hw3
            "/home/coder/project/hw1/hw2/main.c",    # hw1 안의 hw2
            "/home/coder/project/hw1/src/hw1/main",  # 같은 이름의 중첩
        ]
        
        for path in nested_paths:
            result = checker.get_homework_info(path)
            assert result is None, \
                f"Expected None for nested homework path: {path}\nGot: {result}"

    def test_special_cases(self, checker):
        """특수 케이스 테스트"""
        special_cases = [
            # 1. 빈 입력
            "",                                # 빈 문자열
            None,                             # None 입력
            
            # 2. 불완전한 경로
            "/workspace/os-1-202012345",               # 과제 디렉토리 없음
            
            # 3. 잘못된 프로젝트 경로
            "/home/coder/projects/hw1/main",  # 잘못된 projects 디렉토리
            "/home/user/project/hw1/main",    # 잘못된 사용자
        ]
        
        for path in special_cases:
            result = checker.get_homework_info(path)
            assert result is None, \
                f"Expected None for special case: {path}\nGot: {result}" 