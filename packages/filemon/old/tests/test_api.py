import pytest
import aiohttp
import asyncio
from aioresponses import aioresponses
from old.core.api import APIClient

@pytest.fixture
def api_client():
    return APIClient("http://test-server.com")

@pytest.mark.asyncio
async def test_register_snapshot_success(api_client):
    """스냅샷 등록 성공 테스트"""
    with aioresponses() as mocked:
        # API 응답 모킹
        mocked.post(
            "http://test-server.com/api/os-1/hw1/202012180/test.py/20240320_153000",
            status=200
        )
        
        result = await api_client.register_snapshot(
            class_div="os-1",
            hw_name="hw1",
            student_id="202012180",
            filename="test.py",
            timestamp="20240320_153000",
            file_size=1024
        )
        
        assert result is True

@pytest.mark.asyncio
async def test_register_snapshot_failure(api_client):
    """스냅샷 등록 실패 테스트"""
    with aioresponses() as mocked:
        # API 응답 모킹
        mocked.post(
            "http://test-server.com/api/os-1/hw1/202012180/test.py/20240320_153000",
            status=500,
            body="Internal Server Error"
        )
        
        result = await api_client.register_snapshot(
            class_div="os-1",
            hw_name="hw1",
            student_id="202012180",
            filename="test.py",
            timestamp="20240320_153000",
            file_size=1024
        )
        
        assert result is False

@pytest.mark.asyncio
async def test_register_snapshot_network_error(api_client):
    """네트워크 오류 테스트"""
    with aioresponses() as mocked:
        # 네트워크 오류 모킹
        mocked.post(
            "http://test-server.com/api/os-1/hw1/202012180/test.py/20240320_153000",
            exception=aiohttp.ClientError()
        )
        
        result = await api_client.register_snapshot(
            class_div="os-1",
            hw_name="hw1",
            student_id="202012180",
            filename="test.py",
            timestamp="20240320_153000",
            file_size=1024
        )
        
        assert result is False

@pytest.mark.asyncio
async def test_register_snapshot_timeout(api_client):
    """타임아웃 테스트"""
    with aioresponses() as mocked:
        # 타임아웃 모킹
        mocked.post(
            "http://test-server.com/api/os-1/hw1/202012180/test.py/20240320_153000",
            exception=aiohttp.ServerTimeoutError()
        )
        
        result = await api_client.register_snapshot(
            class_div="os-1",
            hw_name="hw1",
            student_id="202012180",
            filename="test.py",
            timestamp="20240320_153000",
            file_size=1024
        )
        
        assert result is False 