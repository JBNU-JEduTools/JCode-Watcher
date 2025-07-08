from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from ..process.types import ProcessType

@dataclass
class CommandResult:
    """명령어 파싱 결과
    
    Attributes:
        source_files: 소스 파일들의 완전한 절대 경로 목록
            예: ["/os-1-202012345/hw1/main.c", "/os-1-202012345/hw1/utils.c"]
        process_type: 프로세스 타입 (GCC/CLANG/PYTHON)
    """
    source_files: List[str]  
    cwd: str                 
    process_type: ProcessType

class Parser(ABC):
    """명령어 파서 인터페이스"""
    @abstractmethod
    def parse(self, args: str, cwd: str) -> CommandResult:
        """명령어를 파싱하여 소스 파일의 절대 경로를 추출

        Args:
            args: 명령어 인자 문자열
                예: "gcc main.c -o main"
                예: "python3 test.py"
                예: "gcc -I/usr/include main.c utils.c -o program"
            cwd: 현재 작업 디렉토리 (완전한 절대 경로)
                예: "/os-1-202012345/hw1"
                - 상대 경로로 지정된 소스 파일을 절대 경로로 변환하는데 사용
                
        Returns:
            CommandResult:
                - source_files: 소스 파일들의 완전한 절대 경로 목록
                    예: ["/os-1-202012345/hw1/main.c"]
                    예: ["/os-1-202012345/hw1/main.c", "/os-1-202012345/hw1/utils.c"]
                - process_type: 프로세스 타입 (GCC/CLANG/PYTHON)
                
        Note:
            - 입력된 상대 경로는 모두 완전한 절대 경로로 변환되어 반환됨
            - 존재하지 않는 파일 경로는 그대로 반환 (검증하지 않음)
        """
        pass 