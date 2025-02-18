"""파일 필터링 유틸리티"""
import fnmatch
from pathlib import Path
from ..config.settings import Config
from ..utils.logger import get_logger

class FileFilter:
    """파일 필터
    
    설정된 규칙에 따라 파일을 필터링합니다.
    """
    
    def __init__(self):
        """파일 필터 초기화"""
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        self.ignore_patterns = Config.IGNORE_PATTERNS
        self.logger = get_logger(self.__class__.__name__)
        
    def should_ignore(self, file_path: str) -> bool:
        """파일을 무시해야 하는지 확인
        
        Args:
            file_path: 검사할 파일 경로
            
        Returns:
            bool: 무시해야 하면 True, 아니면 False
        """
        try:
            path = Path(file_path)
            
            # 확장자 검사
            if path.suffix not in self.allowed_extensions:
                return True
                
            # 무시 패턴 검사
            return any(fnmatch.fnmatch(file_path, pattern)
                      for pattern in self.ignore_patterns)
                
        except Exception as e:
            self.logger.error(f"파일 경로 검증 실패: {e}")
            return True  # 오류 발생 시 안전하게 무시 