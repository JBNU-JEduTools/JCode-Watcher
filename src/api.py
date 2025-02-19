"""API 클라이언트

API 서버와의 통신을 담당하는 클라이언트입니다.
"""
import aiohttp
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ApiClient:
    """API 클라이언트 클래스"""
    
    def __init__(self, base_url: str):
        if not base_url:
            raise ValueError("API URL이 설정되지 않았습니다")
        self._base_url = base_url.rstrip('/')
        self._session: aiohttp.ClientSession | None = None
        
    async def connect(self) -> None:
        """API 세션 연결"""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
    async def disconnect(self) -> None:
        """API 세션 종료"""
        if self._session:
            await self._session.close()
            self._session = None
            
    async def send_snapshot(self, snapshot_data: Dict[str, Any]) -> None:
        """스냅샷 데이터를 API 서버로 전송

        Args:
            snapshot_data: 전송할 스냅샷 데이터
            
        Raises:
            RuntimeError: API 클라이언트가 초기화되지 않은 경우
            aiohttp.ClientError: API 통신 실패 시
        """
        if not self._session:
            raise RuntimeError("API 클라이언트가 초기화되지 않았습니다")
            
        async with self._session.post(f"{self._base_url}/snapshots", json=snapshot_data) as response:
            response.raise_for_status()
            logger.debug("스냅샷 데이터 전송 성공") 