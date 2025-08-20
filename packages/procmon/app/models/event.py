from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .process_type import ProcessType


@dataclass
class Event:
    """프로세스 이벤트
    
    필수 필드는 항상 존재하고, 선택적 필드는 단계별로 채워집니다.
    """
    # 선택적 (단계별로 채워짐)
    process_type: ProcessType = None

    # 학생 정보 (hostname에서 파싱)
    timestamp: Optional[datetime] = None
    class_div: Optional[str] = None      # 과목-분반 (예: "os-1")
    student_id: Optional[str] = None     # 학번 (예: "202012180")
    
    # 과제 정보
    homework_dir: Optional[str] = None   # 과제 디렉토리 (예: "hw1")
    source_file: Optional[str] = None    # 소스 파일 (예: "main.c")

    @property
    def is_compilation(self) -> bool:
        """컴파일 이벤트 여부"""
        return self.process_type in (ProcessType.GCC, ProcessType.CLANG, ProcessType.GPP) if self.process_type else False

    @property
    def is_execution(self) -> bool:
        """실행 이벤트 여부"""
        return self.process_type == ProcessType.USER_BINARY if self.process_type else False