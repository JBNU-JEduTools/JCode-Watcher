import pytest
from typing import Optional, Dict, List
from src.events.models import EventBuilder, ProcessTypeInfo
from src.bpf.event import RawBpfEvent
from src.handlers.process import ProcessTypeHandler
from src.process.types import ProcessType
from src.homework.checker import HomeworkChecker
from unittest.mock import Mock, patch
from unittest.mock import AsyncMock

class MockHomeworkChecker(HomeworkChecker):
    """테스트용 과제 체커"""
    def __init__(self, homework_dirs: List[str]):
        self.homework_dirs = homework_dirs
        
    def get_homework_info(self, binary_path: str) -> Optional[str]:
        """과제 디렉토리 확인"""
        for hw_dir in self.homework_dirs:
            if hw_dir in binary_path:
                return hw_dir
        return None

class MockProcessFilter:
    """테스트용 프로세스 필터"""
    def __init__(self, homework_checker: HomeworkChecker):
        self.patterns: Dict[ProcessType, List[str]] = {
            ProcessType.GCC: ["gcc"],
            ProcessType.CLANG: ["clang"],
            ProcessType.PYTHON: ["python"],
        }
        self.hw_checker = homework_checker
        
    def get_process_type(self, binary_path: str) -> ProcessType:
        """바이너리 경로로 프로세스 타입 결정"""
        # 1. 시스템 바이너리 체크
        for proc_type, patterns in self.patterns.items():
            if any(pattern in binary_path for pattern in patterns):
                return proc_type
                
        # 2. 과제 디렉토리 내 실행 파일 체크
        if self.hw_checker.get_homework_info(binary_path):
            return ProcessType.USER_BINARY
            
        # 3. 그 외는 무시
        return ProcessType.UNKNOWN

@pytest.fixture
def homework_checker():
    """과제 체커 fixture"""
    return MockHomeworkChecker(homework_dirs=["/home/test/hw1", "/home/test/hw2"])

@pytest.fixture
def process_filter(homework_checker):
    """프로세스 필터 fixture"""
    return MockProcessFilter(homework_checker)

@pytest.mark.asyncio
async def test_process_handler_gcc(process_filter):
    """GCC 프로세스 타입 감지 테스트"""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path="/usr/bin/gcc",
        args="gcc -o test test.c",
        pid=1234,
        cwd="/home/test",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event)  # 이벤트를 그대로 반환하도록 설정
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(event)
    
    # Then
    assert result is not None
    assert result.process is not None
    assert result.process.type == ProcessType.GCC
    next_handler.handle.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_process_handler_clang(process_filter):
    """Clang 프로세스 타입 감지 테스트"""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path="/usr/bin/clang",
        args="clang++ -o test test.cpp",
        pid=1234,
        cwd="/home/test",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event)  # 이벤트를 그대로 반환하도록 설정
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(event)
    
    # Then
    assert result is not None
    assert result.process is not None
    assert result.process.type == ProcessType.CLANG
    next_handler.handle.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_process_handler_python(process_filter):
    """Python 프로세스 타입 감지 테스트"""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path="/usr/bin/python3",
        args="python3 test.py",
        pid=1234,
        cwd="/home/test",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event)  # 이벤트를 그대로 반환하도록 설정
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(event)
    
    # Then
    assert result is not None
    assert result.process is not None
    assert result.process.type == ProcessType.PYTHON
    next_handler.handle.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_process_handler_user_binary(process_filter):
    """사용자 바이너리 프로세스 타입 감지 테스트"""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path="/home/test/hw1/myprogram",  # 과제 디렉토리 내 바이너리
        args="./myprogram arg1 arg2",
        pid=1234,
        cwd="/home/test/hw1",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event)  # 이벤트를 그대로 반환하도록 설정
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(event)
    
    # Then
    assert result is not None
    assert result.process is not None
    assert result.process.type == ProcessType.USER_BINARY
    next_handler.handle.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_process_handler_unknown(process_filter):
    """알 수 없는 프로세스 타입 감지 테스트"""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path="/usr/bin/unknown",
        args="unknown --version",
        pid=1234,
        cwd="/home/test",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)
    
    # When
    result = await handler.handle(event)
    
    # Then
    assert result is None  # UNKNOWN 타입은 무시됨

@pytest.mark.asyncio
async def test_process_handler_error_handling(process_filter):
    """에러 처리 테스트"""
    # Given
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path=None,  # 잘못된 입력
        args=None,
        pid=1234,
        cwd="/home/test",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)

    # When
    result = await handler.handle(event)

    # Then
    assert result is None  # 에러 상황에서 None 반환만 검증

@pytest.mark.asyncio
async def test_process_handler_python_script(process_filter):
    """Python 스크립트 실행 감지 테스트"""
    event = EventBuilder(base=RawBpfEvent(
        hostname="test-host",
        binary_path="/usr/bin/python3",
        args="python3 test.py",
        pid=1234,
        cwd="/home/test/hw1",
        error_flags="0",
        exit_code=0
    ))
    handler = ProcessTypeHandler(process_filter)
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=event)
    handler.set_next(next_handler)
    
    result = await handler.handle(event)
    
    assert result is not None
    assert result.process is not None
    assert result.process.type == ProcessType.PYTHON 