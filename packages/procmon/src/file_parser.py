from typing import Set, Optional, List
from .models.process_type import ProcessType
from .utils.logger import logger

class FileParser:
    COMPILER_SKIP_OPTIONS: Set[str] = {
        "-o", "-I", "-include", "-D", "-U", "-MF"
    }
    
    CPP_EXTENSIONS = ['.cpp', '.cc', '.cxx', '.c++', '.C']
    
    def parse(self, process_type: ProcessType, args: List[str]) -> Optional[str]:
        """명령어 인자에서 첫 번째 소스 파일 추출
        
        Args:
            process_type: 프로세스 타입 (GCC, CLANG, GPP, PYTHON 등)
            args: 명령어 인자 리스트
                예: ["main.c", "-o", "program"]
                예: ["script.py", "arg1", "arg2"]
                예: ["-I/usr/include", "test.c", "-o", "test"]
        
        Returns:
            첫 번째 소스 파일명 (상대경로) 또는 None
            예: "main.c", "script.py", "test.c"
        """
        logger.info(*args)
        if not args:
            return None
            
        # ProcessType에 따른 라우팅
        if process_type == ProcessType.PYTHON:
            return self._find_python_file(args)
        elif process_type in (ProcessType.GCC, ProcessType.CLANG, ProcessType.GPP):
            return self._find_c_file(args)
        else:
            return None
    
    def _find_python_file(self, args: List[str]) -> Optional[str]:
        """Python 스크립트 파일 찾기"""
        if '-m' in args:
            return None
            
        for arg in args:
            if arg.endswith('.py') and not arg.startswith('-'):
                return arg
        return None
    
    def _find_c_file(self, args: List[str]) -> Optional[str]:
        """C/C++ 소스 파일 찾기"""
        skip_next = False
        
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            
            if arg in self.COMPILER_SKIP_OPTIONS:
                skip_next = True
                continue
                
            # C 파일 또는 C++ 파일 확인
            if not arg.startswith('-'):
                if arg.endswith('.c'):
                    return arg
                if any(arg.endswith(ext) for ext in self.CPP_EXTENSIONS):
                    return arg
        
        return None