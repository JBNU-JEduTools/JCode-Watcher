from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional
from .process import Process

class ProcessType(Enum):
    """지원하는 프로세스 타입"""
    UNKNOWN = auto()
    GCC = auto()
    CLANG = auto()
    GPP = auto()
    PYTHON = auto()   
    USER_BINARY = auto()

@dataclass(frozen=True)
class Student:
    """학생 정보
    
    호스트네임으로부터 파싱된 학생 정보와 타임스탬프를 포함합니다.
    예시 호스트네임: "jcode-os-1-202012180-hash"
    """
    timestamp: datetime
    class_div: str      # 과목-분반 (예: "os-1")
    student_id: str     # 학번 (예: "202012180")

@dataclass(frozen=True)
class Homework:
    """과제 관련 정보"""
    homework_dir: str
    source_file: Optional[str] = None

class Event:
    """단순한 통합 이벤트
    
    필수 필드는 항상 존재하고, 선택적 필드는 단계별로 채워집니다.
    """
    # 필수 (항상 존재)
    process: Process

    # 선택적 (단계별로 채워짐)
    process_type: Optional[ProcessType] = None
    student_info: Optional[Student] = None
    homework_info: Optional[Homework] = None

    @property
    def is_compilation(self) -> bool:
        """컴파일 이벤트 여부"""
        return self.process_type in (ProcessType.GCC, ProcessType.CLANG, ProcessType.GPP) if self.process_type else False

    @property
    def is_execution(self) -> bool:
        """실행 이벤트 여부"""
        return self.process_type == ProcessType.USER_BINARY if self.process_type else False