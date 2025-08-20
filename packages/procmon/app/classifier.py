import re
from typing import Optional
from .models.process_type import ProcessType
from .models.classification_result import ClassificationResult


class ProcessClassifier:
    """프로세스 바이너리 경로에서 ProcessType 분류"""
    
    # 프로세스 바이너리 경로 정규식 패턴
    PROCESS_PATTERNS = {
        ProcessType.GCC: r"/usr/bin/x86_64-linux-gnu-gcc-\d+",
        ProcessType.CLANG: r"/usr/lib/llvm-\d+/bin/clang",
        ProcessType.GPP: r"/usr/bin/x86_64-linux-gnu-g\+\+-\d+",
        ProcessType.PYTHON: r"/usr/bin/python3\.\d+",
    }
    
    def classify(self, binary_path: str, directory_parser=None) -> ClassificationResult:
        """바이너리 경로에서 ProcessType과 homework 정보 분류
        
        Args:
            binary_path: 실행 파일의 절대 경로
                예: "/usr/lib/llvm-18/bin/clang"
                예: "/usr/bin/python3.11" 
                예: "/home/coder/project/hw1/a.out"
            directory_parser: DirectoryParser 인스턴스 (선택적)
        
        Returns:
            ClassificationResult: 분류 결과 (process_type, homework_dir)
        """
        if not binary_path:
            return ClassificationResult(ProcessType.UNKNOWN)
            
        # 1. 시스템 바이너리 정규식 매칭
        for process_type, pattern in self.PROCESS_PATTERNS.items():
            if re.search(pattern, binary_path):
                return ClassificationResult(process_type)
                
        # 2. 과제 실행 파일 체크 (directory_parser가 제공된 경우에만)
        if directory_parser:
            try:
                hw_dir = directory_parser.parse(binary_path)
                if hw_dir:
                    return ClassificationResult(ProcessType.USER_BINARY, hw_dir)
            except Exception:
                pass
                
        return ClassificationResult(ProcessType.UNKNOWN)