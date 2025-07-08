import pytest
from unittest.mock import AsyncMock, MagicMock
from src.process.types import ProcessType
from src.handlers.api import APIHandler
from src.events.models import EventBuilder, ProcessTypeInfo, EventMetadata, HomeworkInfo
from src.bpf.event import RawBpfEvent
from datetime import datetime

@pytest.fixture
def handler():
    """API 핸들러 fixture"""
    handler = APIHandler()
    handler.client = MagicMock()
    return handler

@pytest.fixture
def python_builder():
    """파이썬 실행을 위한 EventBuilder fixture"""
    base = RawBpfEvent(
        pid=12345,
        binary_path="/usr/bin/python3",
        cwd="/home/coder/project/hw1",
        args="python3 solution.py arg1 arg2",
        error_flags="0b0",
        exit_code=0,
        hostname="jcode-os-1-202012345-abc"
    )
    
    builder = EventBuilder(base)
    builder.process = ProcessTypeInfo(type=ProcessType.PYTHON)
    builder.metadata = EventMetadata(
        timestamp=datetime.now(),
        class_div="os-1",
        student_id="202012345"
    )
    builder.homework = HomeworkInfo(
        homework_dir="hw1",
        source_file="/home/coder/project/hw1/solution.py"
    )
    
    return builder

@pytest.mark.asyncio
async def test_handle_python_execution(handler, python_builder):
    """Python 스크립트 실행 이벤트 처리 테스트"""
    # Given
    handler.client.send_python_execution = AsyncMock(return_value=True)  # send_binary_execution 대신 send_python_execution 사용
    
    # When
    result = await handler.handle(python_builder)
    
    # Then
    assert result is not None
    assert result == python_builder
    handler.client.send_python_execution.assert_awaited_once()  # 파이썬 실행 메서드가 호출되었는지 확인
    args = handler.client.send_python_execution.call_args[0][0]
    assert args.process.type == ProcessType.PYTHON
    assert args.homework.source_file.endswith('solution.py') 