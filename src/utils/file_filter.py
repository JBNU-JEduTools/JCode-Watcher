"""파일 필터링 유틸리티"""
import fnmatch
from pathlib import Path
from ..config.settings import Config

class FileFilter:
    """파일 필터링 클래스"""
    
    def __init__(self):
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        self.ignore_patterns = Config.IGNORE_PATTERNS
        
    def should_ignore(self, file_path: str) -> bool:
        """파일을 무시해야 하는지 확인
        
        Args:
            file_path: 검사할 파일 경로
            
        Returns:
            bool: 무시해야 하면 True, 아니면 False
        """
        path = Path(file_path)
        
        # 확장자 검사
        if path.suffix not in self.allowed_extensions:
            return True
            
        # 무시 패턴 검사
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
                
        return False 