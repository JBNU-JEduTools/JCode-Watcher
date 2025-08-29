import os
import re
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PathFilter:
    """파일 경로 필터링 전담 클래스"""
    
    # 허용되는 파일 패턴 (최대 3depth까지)
    SOURCE_PATTERN_TEMPLATE = r"{base_path}/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/(?:[^/]+/?){{0,4}}[^/]+\.(c|h|py|cpp|hpp)$"
    
    # 무시할 파일 패턴 (정규식)
    IGNORE_PATTERNS = [
        r".*/(?:\.?env|ENV)/.+",          # env, .env, ENV, .ENV
        r".*/(?:site|dist)-packages/.+",   # site-packages, dist-packages
        r".*/lib(?:64|s)?/.+",            # lib, lib64, libs
        r".*/\..+",                        # 숨김 파일/디렉토리
    ]
    
    def __init__(self):
        self.base_path = str(settings.WATCH_ROOT)
        self.source_pattern = self.SOURCE_PATTERN_TEMPLATE.format(base_path=self.base_path)
        logger.debug("PathFilter 초기화됨", base_path=self.base_path, source_pattern=self.source_pattern)
    
    def should_process_file(self, file_path: str) -> bool:
        """파일이 처리 대상인지 확인 (파일 존재 여부도 고려)"""
        logger.debug("파일 처리 대상 검사 시작", file_path=file_path)
        
        # 디렉토리는 무시
        if os.path.isdir(file_path):
            logger.debug("디렉토리이므로 처리 제외", file_path=file_path)
            return False
            
        result = self.should_process_path(file_path)
        logger.debug("파일 처리 대상 검사 완료", file_path=file_path, should_process=result)
        return result
    
    def should_process_path(self, file_path: str) -> bool:
        """파일 경로가 처리 대상인지 확인 (파일 존재 여부와 무관)"""
        logger.debug("경로 처리 대상 검사 시작", file_path=file_path)
        
        # IGNORE_PATTERNS 먼저 체크 (더 빠른 필터링)
        for i, ignore_pattern in enumerate(self.IGNORE_PATTERNS):
            if re.search(ignore_pattern, file_path):
                logger.debug("무시 패턴에 매칭됨", file_path=file_path, 
                           pattern_index=i, pattern=ignore_pattern)
                return False
        
        logger.debug("무시 패턴 검사 통과", file_path=file_path)
        
        # source_pattern 체크
        source_match = re.search(self.source_pattern, file_path)
        if source_match:
            logger.debug("소스 패턴 매칭됨", file_path=file_path, 
                        pattern=self.source_pattern, match_groups=source_match.groups())
            return True
        else:
            logger.debug("소스 패턴 매칭 실패", file_path=file_path, pattern=self.source_pattern)
            return False