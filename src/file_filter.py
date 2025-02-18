"""파일 필터링 모듈"""
import os
import re
import fnmatch
from .config import Config

class FileFilter:
    """파일 필터링을 담당하는 클래스"""
    def __init__(self):
        self.ignore_patterns = self._compile_patterns(Config.IGNORE_PATTERNS)

    def _compile_patterns(self, patterns):
        """와일드카드 패턴을 정규식으로 변환"""
        return [re.compile(fnmatch.translate(p)) for p in patterns]

    def should_ignore(self, file_path):
        """파일이 무시되어야 하는지 확인"""
        # 상대 경로로 변환
        rel_path = os.path.relpath(file_path, Config.BASE_PATH)
        
        # 확장자 검사
        if not file_path.endswith(Config.SUPPORTED_EXTENSIONS):
            return True

        # 무시 패턴 검사
        for pattern in self.ignore_patterns:
            if pattern.match(rel_path) or any(pattern.match(part) 
                for part in rel_path.split(os.sep)):
                return True

        return False 