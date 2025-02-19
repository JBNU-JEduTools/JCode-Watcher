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
from .config.settings import Config

# 모듈 레벨 로거
logger = get_logger(__name__)

class ApiClient:
    """API 클라이언트"""
    
    def __init__(self, api_url: str):
        """
        Args:
            api_url: API 서버 URL
            
        Raises:
            ApiError: API URL이 유효하지 않은 경우
        """
        if not api_url:
            raise ApiError("API URL이 설정되지 않았습니다")
            
        self.api_url = api_url
        self.session: aiohttp.ClientSession = None
        
    async def __aenter__(self) -> 'ApiClient':
        """컨텍스트 매니저 진입
        
        Returns:
            ApiClient: 현재 인스턴스
            
        Raises:
            ApiError: 세션 생성 실패 시
        """
        try:
            self.session = aiohttp.ClientSession()
            return self
        except Exception as e:
            raise ApiError(f"API 세션 생성 실패: {e}") from e
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """컨텍스트 매니저 종료"""
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.error(f"세션 종료 중 오류 발생: {e}")
            finally:
                self.session = None
            
    async def register_snapshot(self, snapshot_data: Dict[str, Any]) -> None:
        """스냅샷 등록
        
        Args:
            snapshot_data: 등록할 스냅샷 데이터
            
        Raises:
            ApiError: API 통신 실패 시 (세션 미초기화, 연결 실패, 타임아웃, SSL 오류 등)
        """
        if not self.session:
            raise ApiError("API 세션이 초기화되지 않았습니다")
            
        try:
            async with self.session.post(
                f"{self.api_url}/snapshots",
                json=snapshot_data,
                timeout=Config.API_TIMEOUT
            ) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    raise ApiError(f"스냅샷 등록 실패 (status: {response.status}): {error_msg}")
                    
                logger.debug(f"스냅샷 등록 성공: {snapshot_data.get('original_path')}")

        except asyncio.TimeoutError:
            raise ApiError(f"API 요청 시간 초과 (timeout: {Config.API_TIMEOUT}초)")
        except aiohttp.ClientError as e:
            raise ApiError(f"API 서버 연결 실패: {e}")
        except ApiError:
            raise
        except Exception as e:
            raise ApiError(f"예상치 못한 API 오류: {e}") from e 