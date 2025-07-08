import pytest
import aiohttp
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock
from aiohttp import web
from src.api.client import APIClient
from src.process.types import ProcessType
from src.events.models import Event, ProcessTypeInfo, EventMetadata, HomeworkInfo
from src.bpf.event import RawBpfEvent

# 테스트용 이벤트 데이터
@pytest.fixture
def sample_event():
    current_time = datetime.now()
    return Event(
        base=RawBpfEvent(
            pid=12345,
            binary_path="/home/coder/project/hw1/main",
            cwd="/home/coder/project/hw1",
            args="./main arg1 arg2",
            error_flags="0b0",
            exit_code=0,
            hostname="jcode-os-1-202012345-abc"
        ),
        process=ProcessTypeInfo(
            type=ProcessType.USER_BINARY
        ),
        metadata=EventMetadata(
            timestamp=current_time,
            class_div="os-1",
            student_id="202012345"
        ),
        homework=HomeworkInfo(
            homework_dir="hw1",
            source_file="/home/coder/project/hw1/main"
        )
    )

@pytest.fixture
def python_event():
    current_time = datetime.now()
    return Event(
        base=RawBpfEvent(
            pid=12345,
            binary_path="/usr/bin/python3",
            cwd="/home/coder/project/hw1",
            args="python3 solution.py arg1 arg2",
            error_flags="0b0",
            exit_code=0,
            hostname="jcode-os-1-202012345-abc"
        ),
        process=ProcessTypeInfo(
            type=ProcessType.PYTHON
        ),
        metadata=EventMetadata(
            timestamp=current_time,
            class_div="os-1",
            student_id="202012345"
        ),
        homework=HomeworkInfo(
            homework_dir="hw1",
            source_file="/home/coder/project/hw1/solution.py"
        )
    )

@pytest.fixture
def api_client():
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = "http://test-api"
        mock_settings.api_timeout = 5.0
        return APIClient()

# 실제 HTTP 서버를 모킹하여 테스트
async def test_send_binary_execution_success(aiohttp_client, sample_event):
    # 테스트용 서버 설정
    async def handler(request):
        # 요청 검증
        assert request.match_info['class_div'] == 'os-1'
        assert request.match_info['hw_dir'] == 'hw1'
        assert request.match_info['student_id'] == '202012345'
        
        # 요청 바디 검증
        data = await request.json()
        assert data['timestamp'] == sample_event.metadata.timestamp.isoformat()
        assert data['exit_code'] == sample_event.base.exit_code
        assert data['cmdline'] == sample_event.base.args
        assert data['cwd'] == sample_event.base.cwd
        assert data['target_path'] == sample_event.base.binary_path
        assert data['process_type'] == 'binary'
        
        return web.json_response({"status": "success"})

    app = web.Application()
    app.router.add_post('/api/{class_div}/{hw_dir}/{student_id}/logs/run', handler)
    
    client = await aiohttp_client(app)
    
    # APIClient 설정
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = str(client.make_url(''))
        mock_settings.api_timeout = 5.0
        api_client = APIClient()
        
        # 테스트 실행
        result = await api_client.send_binary_execution(sample_event)
        assert result is True

async def test_send_compilation_success(aiohttp_client, sample_event):
    # 테스트용 서버 설정
    async def handler(request):
        # 요청 검증
        assert request.match_info['class_div'] == 'os-1'
        assert request.match_info['hw_dir'] == 'hw1'
        assert request.match_info['student_id'] == '202012345'
        
        # 요청 바디 검증
        data = await request.json()
        assert data['timestamp'] == sample_event.metadata.timestamp.isoformat()
        assert data['exit_code'] == sample_event.base.exit_code
        assert data['cmdline'] == sample_event.base.args
        assert data['cwd'] == sample_event.base.cwd
        assert data['binary_path'] == sample_event.base.binary_path
        
        return web.json_response({"status": "success"})

    app = web.Application()
    app.router.add_post('/api/{class_div}/{hw_dir}/{student_id}/logs/build', handler)
    
    client = await aiohttp_client(app)
    
    # APIClient 설정
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = str(client.make_url(''))
        mock_settings.api_timeout = 5.0
        api_client = APIClient()
        
        # 테스트 실행
        result = await api_client.send_compilation(sample_event)
        assert result is True

async def test_api_error_handling(aiohttp_client, sample_event):
    # 테스트용 서버 설정
    async def handler(request):
        # 500 에러 응답
        return web.Response(status=500, text="Internal Server Error")

    app = web.Application()
    app.router.add_post('/api/{class_div}/{hw_dir}/{student_id}/logs/run', handler)
    
    client = await aiohttp_client(app)
    
    # APIClient 설정
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = str(client.make_url(''))
        mock_settings.api_timeout = 5.0
        api_client = APIClient()
        
        # 테스트 실행
        result = await api_client.send_binary_execution(sample_event)
        assert result is False

async def test_network_error_handling(api_client, sample_event):
    # 잘못된 엔드포인트로 설정하여 네트워크 오류 시뮬레이션
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = "http://non-existent-endpoint"
        mock_settings.api_timeout = 1.0
        api_client = APIClient()
        
        # 테스트 실행
        result = await api_client.send_binary_execution(sample_event)
        assert result is False

async def test_timeout_handling(aiohttp_client, sample_event):
    # 테스트용 서버 설정 - 의도적으로 지연 발생
    async def handler(request):
        await asyncio.sleep(2)  # 2초 지연
        return web.json_response({"status": "success"})

    app = web.Application()
    app.router.add_post('/api/{class_div}/{hw_dir}/{student_id}/logs/run', handler)
    
    client = await aiohttp_client(app)
    
    # APIClient 설정 - 1초 타임아웃
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = str(client.make_url(''))
        mock_settings.api_timeout = 1.0
        api_client = APIClient()
        
        # 테스트 실행
        result = await api_client.send_binary_execution(sample_event)
        assert result is False

async def test_send_python_execution_success(aiohttp_client, python_event):
    # 테스트용 서버 설정
    async def handler(request):
        # 요청 검증
        assert request.match_info['class_div'] == 'os-1'
        assert request.match_info['hw_dir'] == 'hw1'
        assert request.match_info['student_id'] == '202012345'
        
        # 요청 바디 검증
        data = await request.json()
        assert data['timestamp'] == python_event.metadata.timestamp.isoformat()
        assert data['exit_code'] == python_event.base.exit_code
        assert data['cmdline'] == python_event.base.args
        assert data['cwd'] == python_event.base.cwd
        assert data['target_path'] == python_event.homework.source_file
        assert data['process_type'] == 'python'
        
        return web.json_response({"status": "success"})

    app = web.Application()
    app.router.add_post('/api/{class_div}/{hw_dir}/{student_id}/logs/run', handler)
    
    client = await aiohttp_client(app)
    
    # APIClient 설정
    with patch('src.api.client.settings') as mock_settings:
        mock_settings.api_endpoint = str(client.make_url(''))
        mock_settings.api_timeout = 5.0
        api_client = APIClient()
        
        # 테스트 실행
        result = await api_client.send_python_execution(python_event)
        assert result is True 