import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.source_path_filter import PathFilter
from app.config import settings


@pytest.fixture
def path_filter(mocker):
    """테스트를 위한 PathFilter 인스턴스를 생성하는 Fixture"""
    # path_filter 모듈이 사용하는 settings 객체 자체를 모킹합니다.
    mock_settings = MagicMock()
    mock_settings.WATCH_ROOT = Path("/watcher/codes")
    mocker.patch('app.source_path_filter.settings', mock_settings)
    return PathFilter()


# 테스트 케이스를 (설명, 경로, 예상결과) 튜플로 정의
path_test_cases = [
    # === 유효한 경로 ===
    ("기본 유효 경로", "/watcher/codes/class-1-202012345/hw1/test.c", True),
    ("다른 과목 및 학번", "/watcher/codes/os-2-202112345/hw5/src/test.py", True),
    ("최대 허용 깊이 (3)", "/watcher/codes/ds-4-202312345/hw2/a/b/c/main.hpp", True),
    ("hw0 허용", "/watcher/codes/class-1-202012345/hw0/test.c", True),
    ("hw10 허용", "/watcher/codes/algo-1-202012345/hw10/util.cpp", True),

    # === 무효한 경로 ===
    # 깊이 초과
    ("허용 깊이 초과 (4)", "/watcher/codes/ds-4-202312345/hw2/a/b/c/d/main.hpp", False),
    # 무시 패턴
    ("lib 디렉토리", "/watcher/codes/algo-3-202212345/hw10/lib/util.cpp", False),
    (".git 디렉토리", "/watcher/codes/class-1-202012345/hw1/.git/config", False),
    ("숨김 파일", "/watcher/codes/class-1-202012345/hw1/.DS_Store", False),
    # 잘못된 과제 번호
    ("잘못된 hw 번호 (hw11)", "/watcher/codes/class-1-202012345/hw11/test.c", False),
    # 잘못된 확장자
    ("잘못된 확장자 (txt)", "/watcher/codes/class-1-202012345/hw1/test.txt", False),
    # 잘못된 경로 구조
    ("학번 폴더 누락", "/watcher/codes/class-1/hw1/test.c", False),
    ("과제 폴더 누락", "/watcher/codes/class-1-202012345/test.c", False),
    ("WATCH_ROOT 외부 경로", "/another/path/class-1-202012345/hw1/test.c", False),
    ("빈 경로", "", False),
]

@pytest.mark.parametrize("description, path, expected", path_test_cases, ids=[c[0] for c in path_test_cases])
def test_path_filtering_logic(path_filter, description, path, expected):
    """다양한 경로에 대해 should_process가 올바르게 동작하는지 통합 테스트"""
    assert path_filter.should_process(path) == expected


def test_should_process_ignores_directories(path_filter, mocker):
    """
    should_process가 디렉토리를 올바르게 처리하는지 테스트
    """
    test_path = "/watcher/codes/class-1-202012345/hw1/some_dir"
    assert path_filter.should_process(test_path) is False

def test_should_process_processes_files(path_filter, mocker):
    """
    should_process가 파일 경로를 올바르게 처리하는지 테스트
    """
    test_path = "/watcher/codes/class-1-202012345/hw1/test.c"
    assert path_filter.should_process(test_path) is True
