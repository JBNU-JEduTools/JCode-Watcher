import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from pathlib import Path
from typing import Optional

from src.handlers.homework import HomeworkHandler
from src.events.models import EventBuilder, EventMetadata, ProcessTypeInfo, HomeworkInfo
from src.bpf.event import RawBpfEvent
from src.process.types import ProcessType
from src.homework.checker import HomeworkChecker

class MockHomeworkChecker(HomeworkChecker):
    """테스트용 과제 체커"""
    def __init__(self, homework_dirs: list[str]):
        self.homework_dirs = homework_dirs
        
    def get_homework_info(self, binary_path: str) -> Optional[str]:
        """과제 디렉토리 확인"""
        for hw_dir in self.homework_dirs:
            if hw_dir in binary_path:
                return hw_dir
        return None

@pytest.fixture
def homework_dirs():
    """테스트용 과제 디렉토리 목록"""
    return ["/home/student/hw1", "/home/student/hw2"]

@pytest.fixture
def handler(homework_dirs):
    """HomeworkHandler 인스턴스를 생성합니다."""
    return HomeworkHandler(MockHomeworkChecker(homework_dirs))

@pytest.fixture
def compiler_event():
    """컴파일러 실행 이벤트를 생성합니다."""
    return RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/gcc",        # 컴파일러 실행 파일
        cwd="/home/student/hw1",           # 과제 디렉토리
        args="gcc -o main main.c",         # 컴파일 명령어
        error_flags="0",
        exit_code=0
    )

@pytest.fixture
def gpp_event():
    """g++ 컴파일러 실행 이벤트를 생성합니다."""
    return RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/g++",        # g++ 컴파일러 실행 파일
        cwd="/home/student/hw1",           # 과제 디렉토리
        args="g++ -o main main.cpp",       # 컴파일 명령어
        error_flags="0",
        exit_code=0
    )

@pytest.fixture
def binary_event():
    """컴파일된 바이너리 실행 이벤트를 생성합니다."""
    return RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1235,
        binary_path="/home/student/hw1/main",  # 컴파일된 실행 파일
        cwd="/home/student/hw1",
        args="./main arg1 arg2",              # 실행 명령어
        error_flags="0",
        exit_code=0
    )

@pytest.fixture
def compiler_builder(compiler_event):
    """컴파일러 이벤트에 대한 EventBuilder를 생성합니다."""
    builder = EventBuilder(compiler_event)
    builder.process = ProcessTypeInfo(type=ProcessType.GCC)
    builder.metadata = EventMetadata(
        timestamp=datetime.now(timezone.utc),
        class_div="os-1",
        student_id="202012180"
    )
    return builder

@pytest.fixture
def gpp_builder(gpp_event):
    """g++ 컴파일러 이벤트에 대한 EventBuilder를 생성합니다."""
    builder = EventBuilder(gpp_event)
    builder.process = ProcessTypeInfo(type=ProcessType.GPP)
    builder.metadata = EventMetadata(
        timestamp=datetime.now(timezone.utc),
        class_div="os-1",
        student_id="202012180"
    )
    return builder

@pytest.fixture
def binary_builder(binary_event):
    """바이너리 실행 이벤트에 대한 EventBuilder를 생성합니다."""
    builder = EventBuilder(binary_event)
    builder.process = ProcessTypeInfo(type=ProcessType.USER_BINARY)
    builder.metadata = EventMetadata(
        timestamp=datetime.now(timezone.utc),
        class_div="os-1",
        student_id="202012180"
    )
    return builder

@pytest.fixture
def python_event():
    """Python 실행 이벤트"""
    return RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/python3",
        cwd="/home/student/hw1",
        args="python3 solution.py",
        error_flags="0",
        exit_code=0
    )

@pytest.fixture
def python_builder(python_event):
    """Python 이벤트에 대한 EventBuilder를 생성합니다."""
    builder = EventBuilder(python_event)
    builder.process = ProcessTypeInfo(type=ProcessType.PYTHON)
    builder.metadata = EventMetadata(
        timestamp=datetime.now(timezone.utc),
        class_div="os-1",
        student_id="202012180"
    )
    return builder

@pytest.mark.asyncio
async def test_handle_compilation_in_homework_dir(handler, compiler_builder):
    """과제 디렉토리 내에서의 컴파일 이벤트 처리를 테스트합니다."""
    # Given
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=compiler_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(compiler_builder)
    
    # Then
    assert result == compiler_builder
    assert isinstance(result.homework, HomeworkInfo)
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file == "/home/student/hw1/main.c"  # 절대 경로로 변경
    next_handler.handle.assert_awaited_once_with(compiler_builder)

@pytest.mark.asyncio
async def test_handle_binary_in_homework_dir(handler, binary_builder):
    """과제 디렉토리 내에서의 바이너리 실행을 테스트합니다."""
    # Given
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=binary_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(binary_builder)
    
    # Then
    assert result == binary_builder
    assert isinstance(result.homework, HomeworkInfo)
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file is None  # 바이너리 실행시에는 소스 파일 정보가 필요 없음
    next_handler.handle.assert_awaited_once_with(binary_builder)

@pytest.mark.asyncio
async def test_handle_compilation_outside_homework_dir(handler, compiler_builder):
    """과제 디렉토리 외부에서의 컴파일 이벤트 처리를 테스트합니다."""
    # Given
    compiler_builder.base = RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/gcc",
        cwd="/home/student/other",          # 과제 디렉토리가 아님
        args="gcc -o test test.c",
        error_flags="0",
        exit_code=0
    )
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=compiler_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(compiler_builder)
    
    # Then
    assert result is None  # 과제 디렉토리 외부면 None 반환
    next_handler.handle.assert_not_called()  # 과제 외 활동은 다음 핸들러로 전달하지 않음

@pytest.mark.asyncio
async def test_handle_non_compilation_in_homework_dir(handler, compiler_builder):
    """과제 디렉토리 내에서의 비컴파일 이벤트 처리를 테스트합니다."""
    # Given
    compiler_builder.process = ProcessTypeInfo(type=ProcessType.PYTHON)
    compiler_builder.base = RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/home/student/hw1/script.py",  # 과제 디렉토리 내 Python 파일
        cwd="/home/student/hw1",
        args="python script.py",
        error_flags="0",
        exit_code=0
    )
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=compiler_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(compiler_builder)
    
    # Then
    assert result == compiler_builder
    assert result.homework is not None  # 과제 디렉토리는 설정되어야 함
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file == "/home/student/hw1/script.py"  # Python 파일 경로 저장
    next_handler.handle.assert_awaited_once_with(compiler_builder)

@pytest.mark.asyncio
async def test_handle_python_in_homework_dir(handler, python_builder):
    """과제 디렉토리 내에서의 Python 실행을 테스트합니다."""
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=python_builder)
    handler.set_next(next_handler)
    
    result = await handler.handle(python_builder)
    
    assert result == python_builder
    assert isinstance(result.homework, HomeworkInfo)
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file == "/home/student/hw1/solution.py"

@pytest.mark.asyncio
async def test_handle_gpp_compilation_in_homework_dir(handler, gpp_builder):
    """과제 디렉토리 내에서의 g++ 컴파일 이벤트 처리를 테스트합니다."""
    # Given
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=gpp_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(gpp_builder)
    
    # Then
    assert result == gpp_builder
    assert isinstance(result.homework, HomeworkInfo)
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file == "/home/student/hw1/main.cpp"  # 절대 경로로 변경
    next_handler.handle.assert_awaited_once_with(gpp_builder)

@pytest.mark.asyncio
async def test_handle_gpp_with_multiple_source_files(handler, gpp_builder):
    """여러 C++ 소스 파일을 처리하는 g++ 이벤트를 테스트합니다."""
    # Given
    gpp_builder.base = RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/g++",
        cwd="/home/student/hw1",
        args="g++ -o program main.cpp helper.cc utils.cxx",  # 여러 확장자의 C++ 파일
        error_flags="0",
        exit_code=0
    )
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=gpp_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(gpp_builder)
    
    # Then
    assert result == gpp_builder
    assert isinstance(result.homework, HomeworkInfo)
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file == "/home/student/hw1/main.cpp"  # 첫 번째 소스 파일
    next_handler.handle.assert_awaited_once_with(gpp_builder)

@pytest.mark.asyncio
async def test_handle_gpp_with_c_source_file(handler, gpp_builder):
    """g++로 C 소스 파일을 컴파일하는 이벤트를 테스트합니다."""
    # Given
    gpp_builder.base = RawBpfEvent(
        hostname="jcode-os-1-202012180-hash",
        pid=1234,
        binary_path="/usr/bin/g++",
        cwd="/home/student/hw1",
        args="g++ -o program main.c",  # C 파일을 g++로 컴파일
        error_flags="0",
        exit_code=0
    )
    next_handler = Mock()
    next_handler.handle = AsyncMock(return_value=gpp_builder)
    handler.set_next(next_handler)
    
    # When
    result = await handler.handle(gpp_builder)
    
    # Then
    assert result == gpp_builder
    assert isinstance(result.homework, HomeworkInfo)
    assert result.homework.homework_dir == "/home/student/hw1"
    assert result.homework.source_file == "/home/student/hw1/main.c"
    next_handler.handle.assert_awaited_once_with(gpp_builder) 