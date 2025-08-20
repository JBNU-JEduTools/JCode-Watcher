from pathlib import Path
from .base import Parser, CommandResult
from ..process.types import ProcessType
from ..config.settings import settings
from ..utils.logging import get_logger

class CCompilerParser(Parser):
    """gcc/clang 명령어 파서"""
    def __init__(self, process_type: ProcessType):
        self.process_type = process_type
        self.logger = get_logger(__name__)
        self.skip_options = settings.COMPILER_SKIP_OPTIONS
        self.logger.info(f"[CCompilerParser] {process_type.name} 파서 초기화 완료")
    
    def parse(self, args: str, cwd: str) -> CommandResult:
        """컴파일러 명령어 파싱

        Args:
            args: 명령어 인자 문자열
                예시: "main.c -o main"
                예시: "-I/usr/include test.c -o test"
            cwd: 현재 작업 디렉토리 (절대 경로)
                예시: "/home/coder/project/hw1"

        Returns:
            CommandResult:
                - source_files: 소스 파일 절대 경로 목록 (예: ["/home/coder/project/hw1/main.c"])
                - cwd: 현재 작업 디렉토리 (입력값 그대로)
                - process_type: 컴파일러 타입 (GCC 또는 CLANG)

        Note:
            다음 옵션과 그 뒤의 인자는 무시됨: {-o, -I, -include, -D, -U, -MF}
        """
        self.logger.debug(f"[CCompilerParser] 명령어 파싱 시작: {args}")
        args_list = args.split()
        source_files = []
        skip_next = False
        
        for arg in args_list:
            if skip_next:
                skip_next = False
                continue
            
            if arg in self.skip_options:
                self.logger.debug(f"[CCompilerParser] 옵션 스킵: {arg}")
                skip_next = True
                continue
                
            if arg.endswith('.c') and not arg.startswith('-'):
                full_path = Path(cwd) / arg
                resolved_path = str(full_path.resolve())
                source_files.append(resolved_path)
                self.logger.debug(f"[CCompilerParser] 소스 파일 발견: {resolved_path}")
        
        result = CommandResult(
            source_files=source_files,
            cwd=cwd,
            process_type=self.process_type
        )
        self.logger.debug(f"[CCompilerParser] 명령어 파싱 완료: {result}")
        return result 