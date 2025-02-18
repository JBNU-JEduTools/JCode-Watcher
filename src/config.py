"""설정 관리 모듈"""
import os
from pathlib import Path

class Config:
    # 기본 경로 설정
    BASE_PATH = os.getenv('WATCHER_BASE_PATH', '/watcher/codes')
    SNAPSHOT_PATH = os.getenv('WATCHER_SNAPSHOT_PATH', '/watcher/snapshots')
    # 감시 설정
    WATCH_PATTERN = os.getenv('WATCHER_PATTERN', "*/config/workspace")
    HOMEWORK_PATTERN = os.getenv('HOMEWORK_PATTERN', "hw*")
    QUEUE_SIZE = int(os.getenv('QUEUE_SIZE', '65536'))

    # 지원하는 파일 확장자
    SUPPORTED_EXTENSIONS = tuple(
        os.getenv('SUPPORTED_EXTENSIONS', '.c,.cpp,.h,.hpp,.py,.java').split(',')
    )

    # 무시할 파일/디렉토리 패턴
    IGNORE_PATTERNS = {
        # 시스템 파일
        '.DS_Store', 'Thumbs.db', '.git', '__pycache__', '*.pyc',
        # 빌드 디렉토리
        'build/', 'dist/', 'target/', 'node_modules/',
        # 로그 파일
        '*.log',
        # 바이너리/오브젝트 파일
        '*.o', '*.so', '*.dylib', '*.dll', '*.exe', '*.out',
        # IDE 설정
        '.idea/', '.vscode/', '.vs/',
        # 기타
        '*.tmp', '*.temp', '*.swp', '~*'
    }

    @classmethod
    def init_directories(cls):
        """필요한 디렉토리 생성"""
        Path(cls.SNAPSHOT_PATH).mkdir(parents=True, exist_ok=True) 