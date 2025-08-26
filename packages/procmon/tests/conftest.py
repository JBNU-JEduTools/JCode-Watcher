import sys
import os
import pytest
from unittest.mock import Mock

# 프로젝트 루트와 app 디렉토리를 Python path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_path = os.path.join(project_root, 'app')

sys.path.insert(0, project_root)
sys.path.insert(0, app_path)


@pytest.fixture
def mock_logger():
    """테스트용 모킹 로거 픽처"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture(autouse=True)
def setup_logging():
    """테스트 실행 시 로깅 설정 초기화"""
    # 테스트 중에는 실제 로깅 설정을 하지 않음
    pass


@pytest.fixture
def sample_process_data():
    """테스트에서 사용할 샘플 프로세스 데이터"""
    return {
        "pid": 1234,
        "hostname": "jcode-os-1-202012345",
        "binary_path": "/usr/bin/x86_64-linux-gnu-gcc-11",
        "cwd": "/workspace/os-1-202012345/hw1",
        "args": ["gcc", "-o", "main", "main.c"],
        "exit_code": 0
    }