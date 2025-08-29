import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch

# 프로젝트 루트와 app 디렉토리를 Python path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_path = os.path.join(project_root, 'app')

sys.path.insert(0, project_root)
sys.path.insert(0, app_path)

from app.path_filter import PathFilter


@pytest.fixture
def real_path_filter():
    """실제 PathFilter"""
    return PathFilter()


@pytest.fixture
def mock_os():
    """테스트용 os 모듈 모킹 (PathFilter 테스트용)"""
    with patch('app.path_filter.os') as mock:
        mock.path.isdir.return_value = False
        mock.path.exists.return_value = True
        yield mock