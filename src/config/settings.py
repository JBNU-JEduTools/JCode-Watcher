import os
from pathlib import Path

# 기본 경로 설정
BASE_DIR = Path("/watcher")

# 감시 설정
WATCH_PATH = BASE_DIR / "codes"
SNAPSHOT_DIR = BASE_DIR / "snapshots"

# API 설정
API_URL = os.getenv("API_URL", "http://localhost:8000")

# 파일 처리 설정
MAX_FILE_SIZE = 64 * 1024  # 64KB

# 허용되는 파일 패턴
SOURCE_PATTERNS = [
    # 각 depth별 허용 패턴 (hw1-hw10만 허용)
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+\.(c|h|py)$",                     # 0depth
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+/[^/]+\.(c|h|py)$",              # 1depth
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+/[^/]+/[^/]+\.(c|h|py)$",        # 2depth
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+/[^/]+/[^/]+/[^/]+\.(c|h|py)$"   # 3depth
]

# 무시할 파일 패턴
IGNORE_PATTERNS = [
    # 4depth 이상 차단
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+/[^/]+/[^/]+/[^/]+/[^/]+/.*$",
    # hw0, hw11 이상의 모든 과제 디렉토리 차단
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:0|[1-9][1-9]|[2-9]\d+)/.*$",
    # 컴파일된 파일과 임시 파일들
    r".*\.(pyc|pyo|pyd|git|o|obj|exe|bin)$",
    # 특수 디렉토리
    r".*/__pycache__/.*",
    r".*/\..+",                  # 숨김 파일/디렉토리
    r".*/build/.*",              # 빌드 디렉토리
    r".*/tmp/.*",               # 임시 디렉토리
    r".*/.cache/.*",            # 캐시 디렉토리
    r".*/Microsoft/.*"          # Microsoft 관련 디렉토리
    r".*/config/.*"          # Microsoft 관련 디렉토리
]

# 로깅 설정
LOG_LEVEL = os.getenv('WATCHER_LOG_LEVEL', 'INFO') 