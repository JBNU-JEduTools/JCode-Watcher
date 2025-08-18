from typing import List
from pathlib import Path

from .base import Parser, CommandResult
from ..process.types import ProcessType
from ..utils.logging import get_logger

class PythonParser(Parser):
    """Python 인터프리터 명령어 파서
    
    python 명령어에서 실행되는 소스 파일을 추출합니다.
    예시:
    - python test.py
    - python3 /home/user/test.py arg1 arg2
    - python -m pytest test_file.py
    """
    
    def __init__(self, process_type: ProcessType):
        self.logger = get_logger(__name__)
        self.process_type = process_type
        self.logger.info(f"[PythonParser] {process_type.name} 파서 초기화 완료")
    
    def parse(self, args: str, cwd: str) -> CommandResult:
        """Python 명령어에서 소스 파일 경로를 추출합니다.
        
        Args:
            args: 명령어 인자 문자열
                예: "script.py arg1 arg2"
                예: "script.py --verbose -o output.txt"
                예: "-m pytest test_file.py"
            cwd: 현재 작업 디렉토리
        """
        try:
            if not args or args.isspace():
                self.logger.debug("[PythonParser] 빈 명령어")
                return CommandResult(source_files=[], cwd=cwd, process_type=self.process_type)
            
            args_list = args.split()
            
            # -m 옵션 체크
            if '-m' in args_list:
                self.logger.debug("[PythonParser] -m 옵션이 발견되어 무시됨")
                return CommandResult(source_files=[], cwd=cwd, process_type=self.process_type)
            
            potential_source = None
            for arg in args_list:
                if arg.endswith('.py'):
                    potential_source = arg
                    break
                    
            if not potential_source:
                self.logger.debug("[PythonParser] Python 소스 파일을 찾을 수 없음")
                return CommandResult(source_files=[], cwd=cwd, process_type=self.process_type)
            
            source_path = str(Path(cwd) / potential_source)
            self.logger.debug(f"[PythonParser] Python 소스 파일 발견: {source_path}")
            
            return CommandResult(
                source_files=[source_path],
                cwd=cwd,
                process_type=self.process_type
            )
            
        except Exception as e:
            self.logger.error(f"[PythonParser] Python 명령어 파싱 실패: {str(e)}")
            return CommandResult(source_files=[], cwd=cwd, process_type=self.process_type)
