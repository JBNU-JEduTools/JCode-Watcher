from dataclasses import dataclass
from typing import Optional
from .process_type import ProcessType


@dataclass
class ClassificationResult:
    """프로세스 분류 결과"""
    process_type: ProcessType
    homework_dir: Optional[str] = None
    
    @property
    def is_unknown(self) -> bool:
        """UNKNOWN 타입 여부"""
        return self.process_type == ProcessType.UNKNOWN
        
    @property
    def is_user_binary(self) -> bool:
        """USER_BINARY 타입 여부"""
        return self.process_type == ProcessType.USER_BINARY
        
    @property
    def is_compilation(self) -> bool:
        """컴파일 프로세스 여부"""
        return self.process_type in (ProcessType.GCC, ProcessType.CLANG, ProcessType.GPP)