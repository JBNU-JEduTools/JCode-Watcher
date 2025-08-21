from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from .process_type import ProcessType


@dataclass(frozen=True)
class Event:
    process_type: ProcessType
    timestamp: datetime
    class_div: str     # 과목-분반 (예: "os-1")
    student_id: str  # 학번 (예: "202012180")
    
    homework_dir: Optional[str] = None   # 과제 디렉터리 ("hw1")
    source_file: Optional[str] = None    # 소스 파일 절대 경로 (컴파일/Python 시)
    
    # Process 정보 (Sender에서 필요)
    exit_code: Optional[int] = None      # 프로세스 종료 코드
    args: Optional[List[str]] = None     # 프로세스 실행 인자
    cwd: Optional[str] = None            # 현재 작업 디렉토리
    binary_path: Optional[str] = None    # 실행 바이너리 경로

    @property
    def is_compilation(self) -> bool:
        """컴파일 이벤트 여부"""
        return self.process_type.is_compilation if self.process_type else False

    @property
    def is_execution(self) -> bool:
        """실행 이벤트 여부"""
        return self.process_type.is_user_binary or (self.process_type == ProcessType.PYTHON) if self.process_type else False
    
  