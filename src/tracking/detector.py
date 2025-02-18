"""파일 변경 감지 및 추적"""
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.exceptions import WatcherConfigError

class ChangeDetector:
    """파일 시스템 변경 감지 및 추적
    
    지정된 디렉토리 구조에서 모니터링이 필요한 디렉토리들을 찾고
    해당 디렉토리의 파일 변경 사항을 추적합니다.
    
    예상되는 디렉토리 구조:
    /base_path/
    └── {course}-{division}-{student_id}/  # 예: os-3-202012180
        └── config/
            └── workspace/
                └── {homework_dir}/        # 예: hw1, hw2
    """
    
    def __init__(self, base_path: Path, course_pattern: str, homework_pattern: str):
        """
        Args:
            base_path: 기본 검색 경로
            course_pattern: 과목 디렉토리 패턴 (예: "os-*-*")
            homework_pattern: 과제 디렉토리 패턴 (예: "hw*")
            
        Raises:
            WatcherConfigError: 기본 경로가 존재하지 않거나 디렉토리가 아닌 경우
        """
        self.base_path = base_path
        self.course_pattern = course_pattern
        self.homework_pattern = homework_pattern
        self.logger = get_logger(self.__class__.__name__)
        
        self.logger.info(f"변경 감지기 초기화: {base_path}")
        self.logger.debug(f"과목 패턴: {course_pattern}")
        self.logger.debug(f"과제 패턴: {homework_pattern}")
        
        if not self.base_path.exists():
            raise WatcherConfigError(f"기본 경로가 존재하지 않습니다: {self.base_path}")
        elif not self.base_path.is_dir():
            raise WatcherConfigError(f"기본 경로가 디렉토리가 아닙니다: {self.base_path}")
        
    def find_target_directories(self) -> list[Path]:
        """모니터링할 대상 디렉토리 목록 반환
        
        Returns:
            list[Path]: 모니터링할 디렉토리 목록. 빈 리스트는 대상이 없음을 의미
            
        Raises:
            WatcherConfigError: 설정이 올바르지 않거나 디렉토리 검색 중 오류 발생 시
        """
        self.logger.debug(f"대상 디렉토리 검색 시작: {self.base_path}")
        
        try:
            # 기본 경로의 모든 항목 출력
            self.logger.debug("기본 경로의 모든 항목:")
            for item in self.base_path.iterdir():
                self.logger.debug(f"- {item}")
            
            # 학생별 과목 디렉토리 검색 (예: os-3-202012180)
            course_dirs = list(self.base_path.glob(self.course_pattern))
            if not course_dirs:
                self.logger.warning(f"'{self.course_pattern}' 패턴과 일치하는 디렉토리를 찾을 수 없습니다")
                return []  # 정상적인 "없음" 상황
                
            target_dirs = []
            for course_dir in course_dirs:
                if not course_dir.is_dir():
                    self.logger.debug(f"디렉토리 아님, 건너뜀: {course_dir}")
                    continue
                    
                self.logger.debug(f"과목 디렉토리 발견: {course_dir}")
                
                # workspace 디렉토리 경로
                workspace_dir = course_dir / "config" / "workspace"
                if not workspace_dir.exists() or not workspace_dir.is_dir():
                    raise WatcherConfigError(f"workspace 디렉토리가 없거나 올바르지 않음: {workspace_dir}")
                    
                self.logger.debug(f"workspace 디렉토리 발견: {workspace_dir}")
                
                # 과제 디렉토리 검색 (예: hw1, hw2)
                hw_dirs = list(workspace_dir.glob(self.homework_pattern))
                if hw_dirs:
                    # 과제 디렉토리들을 감시 목록에 추가
                    for hw_dir in hw_dirs:
                        if hw_dir.is_dir():
                            target_dirs.append(hw_dir)
                            self.logger.debug(f"과제 디렉토리 발견: {hw_dir}")
                        else:
                            self.logger.debug(f"과제 디렉토리 아님: {hw_dir}")
                else:
                    self.logger.debug(f"'{self.homework_pattern}' 패턴과 일치하는 과제 디렉토리 없음: {workspace_dir}")
                    
            if not target_dirs:
                self.logger.warning("모니터링할 디렉토리를 찾지 못했습니다!")
            else:
                self.logger.info(f"대상 디렉토리 {len(target_dirs)}개 발견:")
                for target_dir in target_dirs:
                    self.logger.info(f"- {target_dir}")
                
            return target_dirs
            
        except WatcherConfigError:
            raise
        except Exception as e:
            raise WatcherConfigError(f"디렉토리 검색 중 오류 발생: {e}") from e 