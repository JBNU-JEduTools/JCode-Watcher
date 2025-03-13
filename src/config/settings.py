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
    # 각 depth별 허용 패턴 (hw1-hw10만 허용, 최대 2depth까지)
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+\.(c|h|py)$",                     # 0depth
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+/[^/]+\.(c|h|py)$",              # 1depth
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[1-9]|10)/[^/]+/[^/]+/[^/]+\.(c|h|py)$",        # 2depth
]

# 무시할 파일 패턴 (정규식)
IGNORE_PATTERNS = [
    r".*/(?:\.?env|ENV)/.+",          # env, .env, ENV, .ENV
    r".*/(?:site|dist)-packages/.+",   # site-packages, dist-packages
    r".*/lib(?:64|s)?/.+",            # lib, lib64, libs
    r".*/\..+",                        # 숨김 파일/디렉토리
]

# 로깅 설정
LOG_LEVEL = os.getenv('WATCHER_LOG_LEVEL', 'INFO') 