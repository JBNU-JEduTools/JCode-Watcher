from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..process.types import ProcessType
from ..bpf.event import RawBpfEvent

# 1. 프로세스 타입 관련 (ProcessTypeHandler)
@dataclass(frozen=True)
class ProcessTypeInfo:
    """프로세스 타입 정보"""
    type: ProcessType

# 2. 메타데이터 관련 (EnrichmentHandler)
@dataclass(frozen=True)
class EventMetadata:
    """이벤트 메타데이터
    
    호스트네임으로부터 파싱된 학생 정보와 타임스탬프를 포함합니다.
    예시 호스트네임: "jcode-os-1-202012180-hash"
    """
    timestamp: datetime
    class_div: str      # 과목-분반 (예: "os-1")
    student_id: str     # 학번 (예: "202012180")

# 3. 과제 정보 관련 (HomeworkHandler)
@dataclass(frozen=True)
class HomeworkInfo:
    """과제 관련 정보"""
    homework_dir: str
    source_file: Optional[str] = None

# 4. 최종 통합 이벤트 (APIHandler에서 사용)
@dataclass(frozen=True)
class Event:
    """통합 이벤트
    
    모든 정보를 flat하게 포함하는 최종 이벤트
    """
    base: RawBpfEvent
    process: ProcessTypeInfo
    metadata: EventMetadata
    homework: Optional[HomeworkInfo] = None

    @property
    def is_compilation(self) -> bool:
        """컴파일 이벤트 여부"""
        return self.process.type in (ProcessType.GCC, ProcessType.CLANG, ProcessType.GPP)

    @property
    def is_execution(self) -> bool:
        """실행 이벤트 여부"""
        return self.process.type == ProcessType.USER_BINARY

# 이벤트 구축을 위한 빌더
class EventBuilder:
    """이벤트 빌더
    
    각 핸들러가 이벤트를 점진적으로 구축하는데 사용
    """
    def __init__(self, base: RawBpfEvent):
        self.base = base
        self.process: Optional[ProcessTypeInfo] = None
        self.metadata: Optional[EventMetadata] = None
        self.homework: Optional[HomeworkInfo] = None
    
    def build(self) -> Event:
        """최종 이벤트 생성
        
        Returns:
            Event: 완성된 이벤트
            
        Raises:
            ValueError: 필수 정보가 누락된 경우
        """
        if not self.process:
            raise ValueError("프로세스 타입 정보 누락")
        if not self.metadata:
            raise ValueError("메타데이터 누락")
            
        return Event(
            base=self.base,
            process=self.process,
            metadata=self.metadata,
            homework=self.homework
        )