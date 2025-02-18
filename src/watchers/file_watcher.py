"""파일 감시 관련 구현"""
import logging
from pathlib import Path

class FileWatcher:
    """파일 감시 클래스"""
    
    def __init__(self, base_path: Path, watch_pattern: str, homework_pattern: str):
        self.base_path = base_path
        self.watch_pattern = watch_pattern
        self.homework_pattern = homework_pattern
        logging.info(f"FileWatcher 초기화: base_path={base_path}")
        logging.info(f"감시 패턴: {watch_pattern}")
        logging.info(f"과제 패턴: {homework_pattern}")
        
        # 기본 경로 존재 여부 확인
        if not self.base_path.exists():
            logging.error(f"기본 경로가 존재하지 않습니다: {self.base_path}")
        elif not self.base_path.is_dir():
            logging.error(f"기본 경로가 디렉토리가 아닙니다: {self.base_path}")
        
    def find_watch_directories(self) -> list[Path]:
        """감시할 디렉토리 목록 반환"""
        watch_dirs = []
        logging.info(f"감시 디렉토리 검색 시작: {self.base_path}")
        
        try:
            # 기본 경로의 모든 항목 출력
            logging.debug("기본 경로의 모든 항목:")
            for item in self.base_path.iterdir():
                logging.debug(f"- {item}")
            
            # 학생 디렉토리 검색 (예: os-3-202012180)
            student_dirs = list(self.base_path.glob(self.watch_pattern))
            if not student_dirs:
                logging.warning(f"'{self.watch_pattern}' 패턴과 일치하는 디렉토리를 찾을 수 없습니다")
                return []
                
            for student_dir in student_dirs:
                if not student_dir.is_dir():
                    logging.debug(f"디렉토리 아님, 건너뜀: {student_dir}")
                    continue
                    
                logging.debug(f"학생 디렉토리 발견: {student_dir}")
                
                # workspace 디렉토리 경로
                workspace_dir = student_dir / "config" / "workspace"
                if not workspace_dir.exists() or not workspace_dir.is_dir():
                    logging.debug(f"workspace 디렉토리 없음: {workspace_dir}")
                    continue
                    
                logging.debug(f"workspace 디렉토리 발견: {workspace_dir}")
                
                # 과제 디렉토리 검색 (예: hw1, hw2)
                hw_dirs = list(workspace_dir.glob(self.homework_pattern))
                if hw_dirs:
                    # 과제 디렉토리들을 감시 목록에 추가
                    for hw_dir in hw_dirs:
                        if hw_dir.is_dir():
                            watch_dirs.append(hw_dir)
                            logging.info(f"과제 디렉토리 감시 추가: {hw_dir}")
                        else:
                            logging.debug(f"과제 디렉토리 아님: {hw_dir}")
                else:
                    logging.debug(f"'{self.homework_pattern}' 패턴과 일치하는 과제 디렉토리 없음: {workspace_dir}")
                    
            if not watch_dirs:
                logging.warning("감시할 디렉토리를 찾지 못했습니다!")
            else:
                logging.info(f"총 {len(watch_dirs)}개의 감시 디렉토리 발견")
                
            return watch_dirs
            
        except Exception as e:
            logging.error(f"디렉토리 검색 중 오류 발생: {e}")
            return [] 