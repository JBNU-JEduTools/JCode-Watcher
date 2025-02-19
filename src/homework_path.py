"""과제 경로 관리

학생들의 과제 제출 디렉토리 구조를 관리하고 경로 정보를 처리합니다.
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Optional, NamedTuple

from .utils.logger import get_logger
from .utils.exceptions import ConfigurationError, FileNotFoundInWorkspaceError, InvalidHomeworkPathError
from .config.settings import Config

# 클래스 레벨 로거
logger = get_logger(__name__)

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
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        self.ignore_patterns = Config.IGNORE_PATTERNS
        
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
                logger.debug(f"Ignored file (extension): {file_path}")
                return True
                
            # 무시 패턴 검사
            if any(fnmatch.fnmatch(file_path, pattern)
                  for pattern in self.ignore_patterns):
                logger.debug(f"Ignored file (pattern): {file_path}")
                return True
                
            return False
                
        except Exception as e:
            logger.error(f"파일 경로 검증 실패: {e}")
            return True  # 오류 발생 시 안전하게 무시
        
    def parse_course_dir(self, dir_name: str) -> Optional[tuple[str, str]]:
        """과목 디렉토리명 파싱
        
        Args:
            dir_name: 과목 디렉토리명 (예: "os-3-202012180")
            
        Returns:
            Optional[tuple[str, str]]: (과목-분반, 학번) 튜플 또는 None
        """
        parts = dir_name.split('-')
        if len(parts) != 3:
            return None
            
        return f"{parts[0]}-{parts[1]}", parts[2]
        
    def find_homework_dirs(self) -> List[str]:
        """과제 디렉토리 검색
        
        Returns:
            List[str]: 발견된 과제 디렉토리 목록
            
        Raises:
            FileNotFoundInWorkspaceError: 필요한 디렉토리를 찾을 수 없는 경우
            ConfigurationError: 파일 시스템 접근 권한 등의 설정 문제 발생 시
        """
        try:
            # 기본 경로 접근 권한 확인
            if not os.access(self.base_path, os.R_OK):
                raise ConfigurationError(f"기본 경로 접근 권한이 없습니다: {self.base_path}")
            
            # 과목별 디렉토리 검색
            try:
                course_dirs = [
                    d for d in self.base_path.glob("*-*-*")
                    if d.is_dir() and self.parse_course_dir(d.name)
                ]
            except PermissionError as e:
                raise ConfigurationError(f"과목 디렉토리 접근 권한이 없습니다: {e}") from e
            
            if not course_dirs:
                logger.info("과목 디렉토리가 없습니다")
                return []
                
            # 과제 디렉토리 검색
            hw_dirs = []
            for course_dir in course_dirs:
                try:
                    workspace = course_dir / "config" / "workspace"
                    if not workspace.exists():
                        logger.warning(f"workspace 디렉토리가 없습니다: {workspace}")
                        continue
                        
                    if not workspace.is_dir():
                        logger.warning(f"workspace가 디렉토리가 아닙니다: {workspace}")
                        continue
                        
                    if not os.access(workspace, os.R_OK):
                        logger.warning(f"workspace 접근 권한이 없습니다: {workspace}")
                        continue
                        
                    dirs = [d for d in workspace.glob("hw*") if d.is_dir()]
                    hw_dirs.extend(str(d) for d in dirs)
                    
                except PermissionError as e:
                    logger.warning(f"과제 디렉토리 접근 실패: {course_dir} - {e}")
                    continue
                    
            if hw_dirs:
                logger.info(f"과제 디렉토리 {len(hw_dirs)}개 발견")
            else:
                logger.info("과제 디렉토리가 없습니다")
                
            return hw_dirs
            
        except ConfigurationError:
            raise
        except Exception as e:
            raise FileNotFoundInWorkspaceError(f"과제 디렉토리 검색 실패: {e}") from e
            
    def parse_path(self, file_path: str) -> HomeworkInfo:
        """과제 파일 경로 파싱
        
        Args:
            file_path: 파싱할 파일 경로
            
        Returns:
            HomeworkInfo: 파싱된 과제 정보
            
        Raises:
            InvalidHomeworkPathError: 경로 형식이 잘못된 경우
            Exception: 예상치 못한 오류 발생 시
        """
        if not file_path:
            raise InvalidHomeworkPathError("파일 경로가 비어있습니다")
            
        path = Path(file_path)
        parts = path.parts
        
        # 최소 경로 깊이 검사 (/watcher/codes/os-3-202012180/config/workspace/hw1/file.c)
        if len(parts) < 6:
            raise InvalidHomeworkPathError(
                f"경로 깊이가 부족합니다: {file_path}"
            )
            
        # 기본 정보 추출
        student_dir = parts[3]  # os-3-202012180
        if not (course_info := self.parse_course_dir(student_dir)):
            raise InvalidHomeworkPathError(
                f"과목 디렉토리 형식이 잘못되었습니다: {student_dir}"
            )
            
        class_div, student_id = course_info
            
        # 과제 디렉토리 찾기
        hw_dir = next((part for part in parts if part.startswith("hw")), None)
        if not hw_dir:
            raise InvalidHomeworkPathError(
                f"과제 디렉토리를 찾을 수 없습니다: {file_path}"
            )
            
        # 파일명 생성
        hw_index = parts.index(hw_dir)
        subpath_parts = parts[hw_index + 1:]
        if not subpath_parts:  # 파일명이 없는 경우
            raise InvalidHomeworkPathError(
                f"파일명이 없습니다: {file_path}"
            )
            
        filename = "@".join(subpath_parts) if len(subpath_parts) > 1 else path.name
            
        return HomeworkInfo(
            class_div=class_div,
            hw_dir=hw_dir,
            student_id=student_id,
            filename=filename,
            original_path=file_path
        )
            
