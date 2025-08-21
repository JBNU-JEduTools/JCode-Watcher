import re
from typing import Optional
from .models.process_type import ProcessType
from .path_parser import PathParser


class ProcessClassifier:
    """프로세스 바이너리 경로에서 ProcessType 분류"""
    
    # 프로세스 바이너리 경로 정규식 패턴
    PROCESS_PATTERNS = {
        ProcessType.GCC: r"/usr/bin/x86_64-linux-gnu-gcc-\d+",
        ProcessType.CLANG: r"/usr/lib/llvm-\d+/bin/clang",
        ProcessType.GPP: r"/usr/bin/x86_64-linux-gnu-g\+\+-\d+",
        ProcessType.PYTHON: r"/usr/bin/python3\.\d+",
    }

    
    def classify(self, binary_path: str) -> ProcessType:
        """바이너리 경로에서 시스템 ProcessType 분류(UNKNOWN/USER_BINARY는 여기서 처리하지 않음)"""
        if not binary_path:
            return ProcessType.UNKNOWN
        for process_type, pattern in self.PROCESS_PATTERNS.items():
            if re.fullmatch(pattern, binary_path):
                return process_type 
        return ProcessType.UNKNOWN