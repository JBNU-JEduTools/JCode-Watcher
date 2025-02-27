"""소스코드 경로 관리

소스코드 파일의 경로 구조를 관리하고 정보를 처리합니다.
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Optional, NamedTuple

from .utils.logger import get_logger
from .utils.exceptions import ConfigError, InvalidSourcePathError
from .config.settings import Config

logger = get_logger(__name__)

class SourceCodeInfo(NamedTuple):
    """소스코드 파일 정보"""
    class_div: str      # 분반 (예: "os-3")
    hw_dir: str         # 작업 디렉토리 (예: "hw1")
    student_id: str     # 학번 (예: "202012180")
    filename: str       # 파일명
    original_path: str  # 원본 파일 경로

class SourceCodePath:
    """소스코드 경로 관리자
    
    소스코드 파일의 경로 구조를 관리하고 유효성을 검증합니다.
    """
    
    def __init__(self, base_path: str):
        """
        Args:
            base_path: 기본 디렉토리 경로
            
        Raises:
            ConfigError: 기본 경로가 유효하지 않은 경우
        """
        if not os.path.isdir(base_path):
            raise ConfigError(f"유효하지 않은 기본 경로: {base_path}")
            
        self.base_path = Path(base_path)
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        self.ignore_patterns = Config.IGNORE_PATTERNS
        
    def is_excluded(self, file_path: str) -> bool:
        """파일이 감시 대상에서 제외되어야 하는지 확인

        다음 조건에 해당하는 파일은 제외됩니다:
        1. 허용되지 않은 확장자
        2. 무시 패턴과 일치하는 파일
        3. 파일 이름이 'main'이 아닌 파일
        4. hw* 디렉토리의 직계 자식이 아닌 파일

        Args:
            file_path: 확인할 파일 경로

        Returns:
            bool: 제외 대상이면 True
        """
        try:
            path = Path(file_path)
            
            # 1. 확장자 필터링
            if self._is_invalid_extension(path):
                return True
                
            # 2. 무시 패턴 필터링
            if self._matches_ignore_pattern(file_path):
                return True

            # 3. hw* 디렉토리 직계 자식 검사
            if not self._is_direct_child_of_hw(path):
                return True
                
            # 4. 메인 파일 필터링
            if not self._is_main_file(path):
                return True
                
            return False
                
        except Exception as e:
            logger.error(f"파일 경로 검증 중 오류가 발생했습니다: {str(e)}")
            return True
            
    def _is_invalid_extension(self, path: Path) -> bool:
        """허용되지 않은 확장자인지 확인"""
        if path.suffix not in self.allowed_extensions:
            logger.debug(f"허용되지 않은 파일 확장자입니다 (허용: {', '.join(self.allowed_extensions)}): {path}")
            return True
        return False
        
    def _matches_ignore_pattern(self, file_path: str) -> bool:
        """무시 패턴과 일치하는지 확인"""
        if any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_patterns):
            logger.debug(f"무시 패턴과 일치하는 파일입니다 (패턴: {', '.join(self.ignore_patterns)}): {file_path}")
            return True
        return False
        
    def _is_direct_child_of_hw(self, path: Path) -> bool:
        """hw* 디렉토리의 직계 자식인지 확인"""
        try:
            info = self.parse_path(str(path))
            # hw* 디렉토리 바로 아래의 파일인지 확인
            parts = path.parts
            hw_index = next((i for i, part in enumerate(parts) if part.startswith("hw")), -1)
            
            if hw_index == -1 or hw_index + 2 != len(parts):
                logger.debug(
                    f"이벤트 필터링: hw* 디렉토리의 직계 자식이 아닌 파일 무시 "
                    f"[{info.class_div}/{info.student_id}/{info.hw_dir}/{path.name}]"
                )
                return False
            return True
        except InvalidSourcePathError:
            logger.debug(f"이벤트 필터링: hw* 디렉토리의 직계 자식이 아닌 파일 무시 ({path})")
            return False
        
    def _is_main_file(self, path: Path) -> bool:
        """파일 이름이 'main'인지 확인"""
        try:
            # 경로 정보 파싱 시도
            info = self.parse_path(str(path))
            if path.stem != 'main':
                logger.debug(
                    f"이벤트 필터링: 파일 이름이 'main'이 아닌 파일 무시 "
                    f"[{info.class_div}/{info.student_id}/{info.hw_dir}/{path.name}]"
                )
                return False
        except InvalidSourcePathError:
            # 파싱 실패 시 기본 로그 출력
            logger.debug(f"이벤트 필터링: 파일 이름이 'main'이 아닌 파일 무시 ({path})")
            return False
        return True
        
    def parse_class_dir(self, dir_name: str) -> Optional[tuple[str, str]]:
        """분반 디렉토리명 파싱
        
        Args:
            dir_name: 분반 디렉토리명 (예: "os-3-202012180")
            
        Returns:
            Optional[tuple[str, str]]: (분반, 학번) 튜플 또는 None
        """
        parts = dir_name.split('-')
        if len(parts) != 3:
            return None
            
        return f"{parts[0]}-{parts[1]}", parts[2]
        
    def find_source_dirs(self) -> List[str]:
        """작업 디렉토리 검색
        
        학생별 hw* 디렉토리를 검색합니다.
        예상 경로: /watcher/codes/{분반-학번}/hw*
        
        Returns:
            List[str]: 발견된 작업 디렉토리 목록
            
        Raises:
            ConfigError: 파일 시스템 접근 권한 등의 설정 문제 발생 시
        """
        if not os.access(self.base_path, os.R_OK):
            raise ConfigError(f"기본 경로 접근 권한이 없습니다: {self.base_path}")
        
        try:
            # 학생 디렉토리 검색
            class_dirs = [
                d for d in self.base_path.glob("*-*-*")
                if d.is_dir() and self.parse_class_dir(d.name)
            ]
            
            # 학생 디렉토리 목록 출력
            if class_dirs:
                logger.debug(
                    "발견된 학생 디렉토리: " + 
                    ", ".join(d.name for d in class_dirs)
                )
            else:
                logger.warning("학생 디렉토리를 찾을 수 없습니다")
                return []
                
            # 각 학생 디렉토리 아래의 hw* 디렉토리 검색
            source_dirs = []
            for class_dir in class_dirs:
                try:
                    dirs = [d for d in class_dir.glob("hw*") if d.is_dir()]
                    if dirs:
                        logger.debug(
                            f"{class_dir.name}의 감시 대상: " +
                            ", ".join(f"{d.parent.name}/{d.name}" for d in dirs)
                        )
                    source_dirs.extend(str(d) for d in dirs)
                except PermissionError:
                    logger.error(f"작업 디렉토리 접근 거부됨: {class_dir}")
            
            if source_dirs:
                logger.info(f"감시 대상 디렉토리 발견: {len(source_dirs)}개")
            else:
                logger.warning("감시할 hw* 디렉토리를 찾을 수 없습니다")
                
            return source_dirs
            
        except PermissionError as e:
            raise ConfigError(f"분반 디렉토리 접근 권한이 없습니다: {e}")
            
    def parse_path(self, file_path: str) -> SourceCodeInfo:
        """소스코드 파일 경로 파싱
        
        예상되는 경로 형식: /watcher/codes/{분반-학번}/hw*/{파일명}
        예시: /watcher/codes/os-3-202012180/hw1/main.c
        
        Args:
            file_path: 파싱할 파일 경로
            
        Returns:
            SourceCodeInfo: 파싱된 소스코드 정보
            
        Raises:
            InvalidSourcePathError: 경로 형식이 잘못된 경우
        """
        if not file_path:
            raise InvalidSourcePathError("파일 경로가 비어있습니다")
            
        path = Path(file_path)
        parts = path.parts
        
        # 최소 경로 깊이 검사 (/watcher/codes/os-3-202012345/hw1/main.c -> 최소 5)
        if len(parts) < 5:
            raise InvalidSourcePathError(
                f"경로 깊이가 부족합니다 (최소 5, 현재 {len(parts)}): {file_path}"
            )
            
        # 기본 정보 추출
        student_dir = parts[3]  # os-3-202012345
        if not (course_info := self.parse_class_dir(student_dir)):
            raise InvalidSourcePathError(
                f"디렉토리 형식이 잘못되었습니다 (예상 형식: 분반-학번): {student_dir}"
            )
            
        class_div, student_id = course_info
            
        # 작업 디렉토리 찾기
        hw_dir = next((part for part in parts if part.startswith("hw")), None)
        if not hw_dir:
            raise InvalidSourcePathError(
                f"작업 디렉토리를 찾을 수 없습니다 (예상 형식: hw*): {file_path}"
            )
            
        # 파일명 생성
        hw_index = parts.index(hw_dir)
        subpath_parts = parts[hw_index + 1:]
        if not subpath_parts:
            raise InvalidSourcePathError(
                f"파일명이 없습니다: {file_path}"
            )
            
        filename = "@".join(subpath_parts) if len(subpath_parts) > 1 else path.name
            
        return SourceCodeInfo(
            class_div=class_div,
            hw_dir=hw_dir,
            student_id=student_id,
            filename=filename,
            original_path=file_path
        ) 