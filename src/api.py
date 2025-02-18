"""API 클라이언트

스냅샷 API 서버와의 통신을 담당합니다.
"""
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import asyncio

from .utils.logger import get_logger
from .utils.exceptions import ApiError

class ApiClient:
    """API 클라이언트"""
    
    def __init__(self, api_url: str):
        """
        Args:
            api_url: API 서버 URL
        """
        self.api_url = api_url
        self.logger = get_logger(self.__class__.__name__)
        self.session: aiohttp.ClientSession = None
        
    async def __aenter__(self) -> 'ApiClient':
        """컨텍스트 매니저 진입 (예외 처리 제거)"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료 (예외 처리 간소화)"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def register_snapshot(self, snapshot_data: Dict[str, Any]) -> None:
        """스냅샷 등록 (오류 처리 간소화)"""
        if not self.session:
            raise RuntimeError("API 세션이 초기화되지 않았습니다")  # 일반 예외 사용
            
        try:
            async with self.session.post(
                f"{self.api_url}/snapshots",
                json=snapshot_data,
                timeout=30.0
            ) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    raise RuntimeError(f"스냅샷 등록 실패: {error_msg}")

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error(f"API 오류: {str(e)}")
            raise 