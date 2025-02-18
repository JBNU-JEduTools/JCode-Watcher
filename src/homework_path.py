"""과제 경로 관리

학생들의 과제 제출 디렉토리 구조를 관리하고 경로 정보를 처리합니다.
"""
import os
from pathlib import Path
from typing import List, Optional, NamedTuple

from .utils.logger import get_logger
from .utils.exceptions import ConfigurationError, FileNotFoundInWorkspaceError

class HomeworkInfo(NamedTuple):
    """과제 파일 정보"""
    class_div: str      # 과목-분반 (예: "os-3")
    hw_dir: str         # 과제 디렉토리 (예: "hw1")
    student_id: str     # 학번 (예: "202012180")
    filename: str       # 파일명
    original_path: str  # 원본 파일 경로

class HomeworkPath:
    """과제 경로 관리자
    
    학생들의 과제 제출 디렉토리 구조를 관리하고 경로 정보를 처리합니다.
    """
    
    def __init__(self, base_path: str):
        """
        Args:
            base_path: 기본 디렉토리 경로
            
        Raises:
            ConfigurationError: 기본 경로가 유효하지 않은 경우
        """
        if not os.path.isdir(base_path):
            raise ConfigurationError(f"유효하지 않은 기본 경로: {base_path}")
            
        self.base_path = Path(base_path)
        self.logger = get_logger(self.__class__.__name__)
        self.watch_dirs: set[str] = set()
        
    def parse_course_dir(self, dir_name: str) -> Optional[tuple[str, str]]:
        """과목 디렉토리명 파싱"""
        parts = dir_name.split('-')
        if len(parts) != 3:
            return None
            
        return f"{parts[0]}-{parts[1]}", parts[2]
        
    def find_homework_dirs(self) -> List[str]:
        """과제 디렉토리 검색"""
        try:
            # 과목별 디렉토리 검색
            course_dirs = [
                d for d in self.base_path.glob("*-*-*")
                if d.is_dir() and self.parse_course_dir(d.name)
            ]
            
            if not course_dirs:
                raise FileNotFoundInWorkspaceError("과목 디렉토리를 찾을 수 없음")
                
            # 과제 디렉토리 검색
            hw_dirs = []
            for course_dir in course_dirs:
                workspace = course_dir / "config" / "workspace"
                if workspace.is_dir():
                    dirs = [d for d in workspace.glob("hw*") if d.is_dir()]
                    hw_dirs.extend(str(d) for d in dirs)
                    
            if not hw_dirs:
                raise FileNotFoundInWorkspaceError("과제 디렉토리를 찾을 수 없음")
                
            self.watch_dirs = set(hw_dirs)
            self.logger.info(f"과제 디렉토리 {len(hw_dirs)}개 발견")
            return hw_dirs
            
        except Exception as e:
            if isinstance(e, FileNotFoundInWorkspaceError):
                raise
            raise FileNotFoundInWorkspaceError(f"디렉토리 검색 실패: {e}") from e
            
    def parse_path(self, file_path: str) -> Optional[HomeworkInfo]:
        """과제 파일 경로 파싱"""
        try:
            path = Path(file_path)
            parts = path.parts
            
            # 기본 정보 추출
            student_dir = parts[3]  # os-3-202012180
            if not (course_info := self.parse_course_dir(student_dir)):
                return None
                
            class_div, student_id = course_info
                
            # 과제 디렉토리 찾기
            hw_dir = next((part for part in parts if part.startswith("hw")), None)
            if not hw_dir:
                return None
                
            # 파일명 생성
            hw_index = parts.index(hw_dir)
            subpath_parts = parts[hw_index + 1:]
            filename = "@".join(subpath_parts) if len(subpath_parts) > 1 else path.name
            
            return HomeworkInfo(
                class_div=class_div,
                hw_dir=hw_dir,
                student_id=student_id,
                filename=filename,
                original_path=file_path
            )
            
        except Exception:
            return None
            
    def is_valid_path(self, file_path: str) -> bool:
        """과제 파일 경로 유효성 검사"""
        if not self.watch_dirs:
            return False
            
        return any(file_path.startswith(dir) for dir in self.watch_dirs) 