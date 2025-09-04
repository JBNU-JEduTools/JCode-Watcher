import os
import re
from pathlib import Path
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PathFilter:
    """
    파일 경로가 처리 대상인지 판단하는 클래스.
    정규식 대신 Python 코드를 사용하여 가독성과 유지보수성을 높임.
    """
    
    # 무시할 경로에 대한 정규식 패턴 (미리 컴파일하여 성능 향상)
    IGNORE_PATTERNS = [
        re.compile(r"/.*/(?:\.?env|ENV)/.+"),
        re.compile(r"/.*/(?:site|dist)-packages/.+"),
        re.compile(r"/.*/lib(?:64|s)?/.+"),
        re.compile(r"/.*/\..+"),  # 숨김 파일/디렉토리
    ]
    
    # 허용할 파일 확장자
    ALLOWED_EXTENSIONS = {".c", ".h", ".py", ".cpp", ".hpp"}

    def __init__(self):
        self.watch_root = settings.WATCH_ROOT
        logger.info("PathFilter 초기화 완료", watch_root=str(self.watch_root))

    def should_process_file(self, file_path: str) -> bool:
        """파일이 처리 대상인지 확인 (디렉토리는 항상 무시)"""
        # 디렉토리는 처리하지 않음
        if os.path.isdir(file_path):
            return False
        return self._should_process(file_path)

    def should_process_path(self, file_path: str) -> bool:
        """경로가 처리 대상인지 확인 (파일/디렉토리 여부 무관)"""
        return self._should_process(file_path)

    def _should_process(self, path_str: str) -> bool:
        """공통 필터링 로직"""
        # 1. 무시 패턴에 해당하는지 먼저 확인
        if self._is_ignored(path_str):
            return False
        
        # 2. 경로 구조가 유효한지 확인
        return self._is_valid_source_path(path_str)

    def _is_ignored(self, path_str: str) -> bool:
        """무시 패턴에 해당하는지 확인"""
        for pattern in self.IGNORE_PATTERNS:
            if pattern.search(path_str):
                return True
        return False

    def _is_valid_source_path(self, path_str: str) -> bool:
        """소스 코드 경로 구조의 유효성을 검사"""
        try:
            path = Path(path_str)
            relative_path = path.relative_to(self.watch_root)
            
            parts = relative_path.parts
            
            # 경로 깊이 검사
            # 최소: class/hw/file.txt (3개 파트)
            # 최대: class/hw/d1/d2/d3/file.txt (6개 파트)
            if not (3 <= len(parts) <= 6):
                return False

            # 1. 과목-분반-학번 폴더 검사 (예: os-1-202012345)
            class_student_parts = parts[0].split('-')
            if len(class_student_parts) != 3:
                return False

            # 2. 과제 폴더 검사 (예: hw1, hw10)
            hw_part = parts[1]
            if not (hw_part.startswith("hw") and hw_part[2:].isdigit() and 0 <= int(hw_part[2:]) <= 10):
                return False

            # 3. 파일 확장자 검사
            if path.suffix not in self.ALLOWED_EXTENSIONS:
                return False
                
            return True
            
        except (ValueError, IndexError):
            # relative_to 실패, split 실패, 인덱스 접근 실패 등 모든 예외는 유효하지 않은 경로로 간주
            return False
