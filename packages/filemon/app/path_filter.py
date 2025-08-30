import os
import re
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PathFilter:
    """파일 경로 필터링 전담 클래스"""
    
    # 허용되는 파일 패턴 (최대 3depth까지)
    SOURCE_PATTERN_TEMPLATE = r"{watch_root}/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/(?:[^/]+/?){{0,3}}[^/]+\.(c|h|py|cpp|hpp)$"
    
    # 무시할 파일 패턴 (정규식)
    IGNORE_PATTERNS = [
        r".*/(?:\.?env|ENV)/.+",          # env, .env, ENV, .ENV
        r".*/(?:site|dist)-packages/.+",   # site-packages, dist-packages
        r".*/lib(?:64|s)?/.+",            # lib, lib64, libs
        r".*/\..+",                        # 숨김 파일/디렉토리
    ]
    
    def __init__(self):
        self.watch_root = str(settings.WATCH_ROOT)
        self.source_pattern = self.SOURCE_PATTERN_TEMPLATE.format(watch_root=self.watch_root)
    
    def should_process_file(self, file_path: str) -> bool:
        """파일이 처리 대상인지 확인 (파일 존재 여부도 고려)"""
        # 디렉토리는 무시
        if os.path.isdir(file_path):
            return False
            
        return self.should_process_path(file_path)
    
    def should_process_path(self, file_path: str) -> bool:
        """파일 경로가 처리 대상인지 확인 (파일 존재 여부와 무관)"""
        # IGNORE_PATTERNS 먼저 체크 (더 빠른 필터링)
        for ignore_pattern in self.IGNORE_PATTERNS:
            if re.search(ignore_pattern, file_path):
                return False
        
        # source_pattern 체크
        return bool(re.search(self.source_pattern, file_path))