import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from aiohttp import ClientSession, ClientResponse
from aiohttp.web_exceptions import HTTPException

from app.sender import EventSender
from app.models.event import Event
from app.models.process_type import ProcessType


@pytest.fixture
def mock_event():
    """테스트용 Event 객체"""
    return Event(
        process_type=ProcessType.GCC,
        homework_dir="hw1",
        student_id="202012345",
        class_div="class-1",
        timestamp=datetime(2025, 8, 26, 12, 0, 0),
        source_file="/workspace/class-1-202012345/hw1/main.c",
        exit_code=0,
        args=["gcc", "-o", "main", "main.c"],
        cwd="/workspace/class-1-202012345/hw1",
        binary_path="/usr/bin/gcc",
    )


@pytest.fixture
def mock_execution_event():
    """실행 이벤트용 Event 객체"""
    return Event(
        process_type=ProcessType.USER_BINARY,
        homework_dir="hw1", 
        student_id="202012345",
        class_div="class-1",
        timestamp=datetime(2025, 8, 26, 12, 0, 0),
        source_file=None,
        exit_code=0,
        args=["./main"],
        cwd="/workspace/class-1-202012345/hw1",
        binary_path="/workspace/class-1-202012345/hw1/main",
    )


@pytest.fixture
def mock_python_event():
    """Python 실행 이벤트용 Event 객체"""
    return Event(
        process_type=ProcessType.PYTHON,
        homework_dir="hw2",
        student_id="202012345", 
        class_div="class-1",
        timestamp=datetime(2025, 8, 26, 12, 0, 0),
        source_file="/workspace/class-1-202012345/hw2/script.py",
        exit_code=0,
        args=["python3", "script.py"],
        cwd="/workspace/class-1-202012345/hw2",
        binary_path="/usr/bin/python3",
    )


@pytest.fixture
def sender():
    """EventSender 인스턴스"""
    return EventSender(base_url="http://localhost:8000", timeout=10)


class TestEventSender:
    """EventSender 테스트"""

    def test_init(self):
        """EventSender 초기화 테스트"""
        sender = EventSender("http://example.com/", 30)
        assert sender.base_url == "http://example.com"
        assert sender.timeout == 30

    def test_validate_event_success(self, sender, mock_event):
        """유효한 이벤트 검증 테스트"""
        assert sender._validate_event(mock_event) is True

    def test_validate_event_missing_class_div(self, sender):
        """class_div 누락 이벤트 검증 테스트"""
        event = Event(
            process_type=ProcessType.GCC,
            homework_dir="hw1",
            student_id="202012345",
            class_div=None,  # 누락
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
            source_file="/workspace/class-1-202012345/hw1/main.c",
            exit_code=0,
            args=["gcc", "-o", "main", "main.c"],
            cwd="/workspace/class-1-202012345/hw1",
            binary_path="/usr/bin/gcc",
        )
        assert sender._validate_event(event) is False

    def test_validate_event_missing_student_id(self, sender):
        """student_id 누락 이벤트 검증 테스트"""
        event = Event(
            process_type=ProcessType.GCC,
            homework_dir="hw1",
            student_id=None,  # 누락
            class_div="class-1",
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
            source_file="/workspace/class-1-202012345/hw1/main.c",
            exit_code=0,
            args=["gcc", "-o", "main", "main.c"],
            cwd="/workspace/class-1-202012345/hw1",
            binary_path="/usr/bin/gcc",
        )
        assert sender._validate_event(event) is False

    def test_validate_event_missing_homework_dir(self, sender):
        """homework_dir 누락 이벤트 검증 테스트"""
        event = Event(
            process_type=ProcessType.GCC,
            homework_dir=None,  # 누락
            student_id="202012345",
            class_div="class-1",
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
            source_file="/workspace/class-1-202012345/hw1/main.c",
            exit_code=0,
            args=["gcc", "-o", "main", "main.c"],
            cwd="/workspace/class-1-202012345/hw1",
            binary_path="/usr/bin/gcc",
        )
        assert sender._validate_event(event) is False

    @pytest.mark.asyncio
    async def test_send_compilation_success(self, sender, mock_event):
        """컴파일 이벤트 전송 성공 테스트"""
        # _send_request 메서드를 직접 mock
        with patch.object(sender, '_send_request', return_value=True) as mock_send:
            result = await sender.send_event(mock_event)
            
            assert result is True
            mock_send.assert_called_once()
            
            # 호출된 인수 확인
            call_args = mock_send.call_args
            expected_endpoint = "/api/class-1/hw1/202012345/logs/build"
            assert call_args[0][0] == expected_endpoint
            
            # JSON 데이터 확인
            data = call_args[0][1]
            assert data["cmdline"] == "gcc -o main main.c"
            assert data["exit_code"] == 0
            assert data["binary_path"] == "/usr/bin/gcc"
            assert data["target_path"] == "/workspace/class-1-202012345/hw1/main.c"

    @pytest.mark.asyncio
    async def test_send_execution_binary_success(self, sender, mock_execution_event):
        """바이너리 실행 이벤트 전송 성공 테스트"""
        # _send_request 메서드를 직접 mock
        with patch.object(sender, '_send_request', return_value=True) as mock_send:
            result = await sender.send_event(mock_execution_event)
            
            assert result is True
            mock_send.assert_called_once()
            
            # 호출된 인수 확인
            call_args = mock_send.call_args
            expected_endpoint = "/api/class-1/hw1/202012345/logs/run"
            assert call_args[0][0] == expected_endpoint
            
            # JSON 데이터 확인
            data = call_args[0][1]
            assert data["cmdline"] == "./main"
            assert data["process_type"] == "binary"
            assert data["target_path"] == "/workspace/class-1-202012345/hw1/main"

    @pytest.mark.asyncio
    async def test_send_execution_python_success(self, sender, mock_python_event):
        """Python 실행 이벤트 전송 성공 테스트"""
        # _send_request 메서드를 직접 mock
        with patch.object(sender, '_send_request', return_value=True) as mock_send:
            result = await sender.send_event(mock_python_event)
            
            assert result is True
            mock_send.assert_called_once()
            
            # 호출된 인수 확인
            call_args = mock_send.call_args
            expected_endpoint = "/api/class-1/hw2/202012345/logs/run"
            assert call_args[0][0] == expected_endpoint
            
            # JSON 데이터 확인
            data = call_args[0][1]
            assert data["cmdline"] == "python3 script.py"
            assert data["process_type"] == "python"
            assert data["target_path"] == "/workspace/class-1-202012345/hw2/script.py"

    @pytest.mark.asyncio
    async def test_send_event_api_error(self, sender, mock_event):
        """API 에러 응답 테스트"""
        with patch('app.sender.aiohttp') as mock_aiohttp:
            # Mock response 설정 - 422 에러
            mock_response = AsyncMock()
            mock_response.status = 422
            mock_response.text.return_value = '{"detail":[{"type":"string_type","loc":["body","cmdline"],"msg":"Input should be a valid string","input":["gcc","hello.c"]}]}'
            
            # Mock session 설정
            mock_session = AsyncMock()
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = mock_session

            result = await sender.send_event(mock_event)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_send_event_validation_failure(self, sender):
        """이벤트 검증 실패 테스트"""
        event = Event(
            process_type=ProcessType.GCC,
            homework_dir="hw1",
            student_id="202012345",
            class_div=None,  # 필수 필드 제거
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
        )
        
        result = await sender.send_event(event)
        assert result is False

    @pytest.mark.asyncio 
    async def test_send_event_unknown_process_type(self, sender):
        """알 수 없는 프로세스 타입 테스트"""
        event = Event(
            process_type=ProcessType.UNKNOWN,
            homework_dir="hw1",
            student_id="202012345",
            class_div="class-1",
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
        )
        
        result = await sender.send_event(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_event_network_exception(self, sender, mock_event):
        """네트워크 예외 테스트"""
        with patch('app.sender.aiohttp') as mock_aiohttp:
            # Mock session에서 예외 발생
            mock_session = AsyncMock()
            mock_session.post.side_effect = Exception("Network error")
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = mock_session

            result = await sender.send_event(mock_event)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_cmdline_list_to_string_conversion(self, sender):
        """cmdline이 리스트에서 문자열로 올바르게 변환되는지 테스트"""
        event = Event(
            process_type=ProcessType.GCC,
            homework_dir="hw1",
            student_id="202012345",
            class_div="class-1",
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
            source_file="/workspace/class-1-202012345/hw1/main.c",
            exit_code=0,
            args=["gcc", "-Wall", "-g", "main.c", "-o", "main"],
            cwd="/workspace/class-1-202012345/hw1",
            binary_path="/usr/bin/gcc",
        )

        with patch('app.sender.aiohttp') as mock_aiohttp:
            # Mock response 설정
            mock_response = AsyncMock()
            mock_response.status = 200
            
            # Mock session 설정
            mock_session = AsyncMock()
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = mock_session

            await sender.send_event(event)
            
            # JSON 데이터에서 cmdline이 문자열로 변환되었는지 확인
            call_args = mock_session.post.call_args
            json_data = call_args[1]["json"]
            assert json_data["cmdline"] == "gcc -Wall -g main.c -o main"
            assert isinstance(json_data["cmdline"], str)

    @pytest.mark.asyncio
    async def test_empty_args_handling(self, sender):
        """빈 args 처리 테스트"""
        event = Event(
            process_type=ProcessType.USER_BINARY,
            homework_dir="hw1",
            student_id="202012345",
            class_div="class-1",
            timestamp=datetime(2025, 8, 26, 12, 0, 0),
            source_file=None,
            exit_code=0,
            args=[],  # 빈 리스트
            cwd="/workspace/class-1-202012345/hw1",
            binary_path="/workspace/class-1-202012345/hw1/main",
        )

        with patch('app.sender.aiohttp') as mock_aiohttp:
            # Mock response 설정
            mock_response = AsyncMock()
            mock_response.status = 200
            
            # Mock session 설정
            mock_session = AsyncMock()
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = mock_session

            await sender.send_event(event)
            
            # JSON 데이터에서 cmdline이 빈 문자열로 처리되었는지 확인
            call_args = mock_session.post.call_args
            json_data = call_args[1]["json"]
            assert json_data["cmdline"] == ""