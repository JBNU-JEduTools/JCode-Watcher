"""파일 감시 관련 구현"""
from pathlib import Path
from ..utils.logger import get_logger
from ..exceptions import FileWatcherError, WatcherConfigError

class FileWatcher:
    """파일 감시 클래스"""
    
    def __init__(self, base_path: Path, watch_pattern: str, homework_pattern: str):
        self.base_path = base_path
        self.watch_pattern = watch_pattern
        self.homework_pattern = homework_pattern
        self.logger = get_logger(self.__class__.__name__)
        
        self.logger.info(f"FileWatcher 초기화: base_path={base_path}")
        self.logger.debug(f"감시 패턴: {watch_pattern}")
        self.logger.debug(f"과제 패턴: {homework_pattern}")
        
        # 기본 경로 존재 여부 확인
        if not self.base_path.exists():
            raise WatcherConfigError(f"기본 경로가 존재하지 않습니다: {self.base_path}")
        elif not self.base_path.is_dir():
            raise WatcherConfigError(f"기본 경로가 디렉토리가 아닙니다: {self.base_path}")
        
    def find_watch_directories(self) -> list[Path]:
        """감시할 디렉토리 목록 반환
        
        Returns:
            list[Path]: 감시할 디렉토리 목록. 빈 리스트는 감시할 디렉토리가 없음을 의미
            
        Raises:
            FileWatcherError: 디렉토리 검색 중 오류 발생 시
            WatcherConfigError: 설정이 올바르지 않은 경우
        """
        self.logger.debug(f"감시 디렉토리 검색 시작: {self.base_path}")
        
        try:
            # 기본 경로의 모든 항목 출력
            self.logger.debug("기본 경로의 모든 항목:")
            for item in self.base_path.iterdir():
                self.logger.debug(f"- {item}")
            
            # 학생 디렉토리 검색 (예: os-3-202012180)
            student_dirs = list(self.base_path.glob(self.watch_pattern))
            if not student_dirs:
                self.logger.warning(f"'{self.watch_pattern}' 패턴과 일치하는 디렉토리를 찾을 수 없습니다")
                return []  # 정상적인 "없음" 상황
                
            watch_dirs = []
            for student_dir in student_dirs:
                if not student_dir.is_dir():
                    self.logger.debug(f"디렉토리 아님, 건너뜀: {student_dir}")
                    continue
                    
                self.logger.debug(f"학생 디렉토리 발견: {student_dir}")
                
                # workspace 디렉토리 경로
                workspace_dir = student_dir / "config" / "workspace"
                if not workspace_dir.exists() or not workspace_dir.is_dir():
                    raise WatcherConfigError(f"workspace 디렉토리가 없거나 올바르지 않음: {workspace_dir}")
                    
                self.logger.debug(f"workspace 디렉토리 발견: {workspace_dir}")
                
                # 과제 디렉토리 검색 (예: hw1, hw2)
                hw_dirs = list(workspace_dir.glob(self.homework_pattern))
                if hw_dirs:
                    # 과제 디렉토리들을 감시 목록에 추가
                    for hw_dir in hw_dirs:
                        if hw_dir.is_dir():
                            watch_dirs.append(hw_dir)
                            self.logger.debug(f"과제 디렉토리 발견: {hw_dir}")
                        else:
                            self.logger.debug(f"과제 디렉토리 아님: {hw_dir}")
                else:
                    self.logger.debug(f"'{self.homework_pattern}' 패턴과 일치하는 과제 디렉토리 없음: {workspace_dir}")
                    
            if not watch_dirs:
                self.logger.warning("감시할 디렉토리를 찾지 못했습니다!")
            else:
                self.logger.info(f"감시할 디렉토리 {len(watch_dirs)}개 발견:")
                for watch_dir in watch_dirs:
                    self.logger.info(f"- {watch_dir}")
                
            return watch_dirs
            
        except WatcherConfigError:
            raise
        except Exception as e:
            raise FileWatcherError(f"디렉토리 검색 중 오류 발생: {e}") from e 