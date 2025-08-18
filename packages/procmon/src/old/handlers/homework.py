import os
from typing import Optional, Dict
from pathlib import Path

from .base import EventHandler
from ..events.models import EventBuilder, HomeworkInfo
from ..homework.checker import HomeworkChecker
from ..process.types import ProcessType
from ..parser.base import Parser
from ..parser.compiler import CCompilerParser
from ..parser.cpp_compiler import CPPCompilerParser
from ..parser.python import PythonParser
from ..utils.logging import get_logger

class HomeworkHandler(EventHandler[EventBuilder, EventBuilder]):
    """과제 정보 처리 핸들러
    
    실행된 프로세스가 과제와 관련된 경우 과제 정보를 추가합니다.
    1. 유저 바이너리인 경우: 실행 파일이 과제 디렉토리 내에 있는지 확인
    2. 컴파일러/인터프리터 프로세스인 경우: 명령어에서 소스 파일을 추출하고 과제 디렉토리 확인
    """
    
    def __init__(self, homework_checker: HomeworkChecker):
        self.logger = get_logger(__name__)
        self.hw_checker = homework_checker
        self.gcc_parser = CCompilerParser(ProcessType.GCC)
        self.clang_parser = CCompilerParser(ProcessType.CLANG)
        self.gpp_parser = CPPCompilerParser(ProcessType.GPP)
        self.python_parser = PythonParser(ProcessType.PYTHON)
    
    def _get_parser(self, process_type: ProcessType) -> Optional[Parser]:
        """프로세스 타입에 맞는 파서를 반환합니다."""
        if process_type == ProcessType.GCC:
            return self.gcc_parser
        elif process_type == ProcessType.CLANG:
            return self.clang_parser
        elif process_type == ProcessType.GPP:
            return self.gpp_parser
        elif process_type == ProcessType.PYTHON:
            return self.python_parser
        return None
    
    async def _handle_user_binary(self, builder: EventBuilder) -> Optional[EventBuilder]:
        """유저 바이너리 실행을 처리합니다."""
        try:
            self.logger.debug(f"바이너리 실행 처리 시작: {builder.base.binary_path}")
            
            hw_dir = self.hw_checker.get_homework_info(builder.base.binary_path)
            if hw_dir:
                builder.homework = HomeworkInfo(homework_dir=hw_dir, source_file=None)
                self.logger.debug(f"과제 정보 설정 완료: binary={builder.base.binary_path}, hw_dir={hw_dir}")
            else:
                self.logger.info(f"과제 디렉토리 외 실행으로 처리 중단: {builder.base.binary_path}")
            return await self._handle_next(builder)
            
        except Exception as e:
            self.logger.error(f"과제 실행 파일 처리 오류: {str(e)}")
            return None

    async def _handle_source_file(self, builder: EventBuilder, parser: Parser) -> Optional[EventBuilder]:
        """소스 파일을 파싱하고 과제 관련 여부를 확인합니다."""
        try:
            self.logger.debug(f"소스 파일 처리 시작: type={builder.process.type}, args={builder.base.args}")
            
            result = parser.parse(builder.base.args, builder.base.cwd)
            if not result.source_files:
                self.logger.info(
                    f"소스 파일을 찾을 수 없어 처리 중단: "
                    f"binary={builder.base.binary_path}, "
                    f"cwd={builder.base.cwd}"
                )
                return None
            
            self.logger.debug(f"소스 파일 발견: count={len(result.source_files)}")
            
            source_file = result.source_files[0]
            hw_dir = self.hw_checker.get_homework_info(source_file)
            if hw_dir:
                builder.homework = HomeworkInfo(homework_dir=hw_dir, source_file=source_file)
                self.logger.debug(f"과제 정보 설정 완료: source={source_file}, hw_dir={hw_dir}")
                return await self._handle_next(builder)
            else:
                self.logger.info(f"과제 외 소스 파일로 처리 중단: {source_file}")
                return None
                
        except Exception as e:
            self.logger.error(f"소스 파일 처리 오류: {str(e)}")
            return None
    
    async def handle(self, builder: EventBuilder) -> Optional[EventBuilder]:
        self.logger.debug("=== 과제 정보 처리 시작 ===")
        self.logger.debug(f"프로세스: {builder.process.type}")
        self.logger.debug(f"실행 파일: {builder.base.binary_path}")
        
        try:
            if builder.process.type == ProcessType.USER_BINARY:
                result = await self._handle_user_binary(builder)
            else:
                parser = self._get_parser(builder.process.type)
                if parser:
                    result = await self._handle_source_file(builder, parser)
                else:
                    self.logger.info(f"지원하지 않는 프로세스 타입으로 처리 중단: {builder.process.type}")
                    return await self._handle_next(builder)
            
            if result and result.homework:
                self.logger.debug(f"과제 정보 처리 완료: dir={result.homework.homework_dir}, source={result.homework.source_file}")
            return result
            
        except Exception as e:
            self.logger.error(f"과제 정보 처리 중 예기치 않은 오류: {str(e)}")
            return await self._handle_next(builder)