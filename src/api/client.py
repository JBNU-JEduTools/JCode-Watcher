"""스냅샷 API 클라이언트"""
import asyncio
import aiohttp
from typing import Optional, Protocol
from .schemas import SnapshotRequest
from ..utils.logger import get_logger
from ..utils.exceptions import ApiError, MetadataError

class ApiClient(Protocol):
    """API 클라이언트 인터페이스"""
    
    async def register_snapshot(self, data: SnapshotRequest) -> None:
        """스냅샷 등록 API 호출
        
        Args:
            data: 등록할 스냅샷 데이터
            
        Raises:
            MetadataError: 메타데이터 등록 실패 시
            ApiError: API 통신 실패 시
        """
        ...

class SnapshotApiClient:
    """스냅샷 API 클라이언트
    
    스냅샷 메타데이터를 API 서버에 등록하고 관리합니다.
    비동기 HTTP 통신을 사용하여 서버와 통신합니다.
    """
    
    def __init__(self, api_url: str = "http://localhost:5000", timeout: float = 5.0):
        """
        Args:
            api_url: API 서버 URL
            timeout: API 요청 타임아웃 (초)
        """
        self.api_url = api_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug(f"API 클라이언트 초기화: {api_url}")
        
    async def __aenter__(self) -> 'SnapshotApiClient':
        """비동기 컨텍스트 매니저 진입
        
        Returns:
            SnapshotApiClient: 현재 인스턴스
            
        Raises:
            ApiError: API 세션 생성 실패 시
        """
        try:
            self.session = aiohttp.ClientSession()
            return self
        except Exception as e:
            raise ApiError(f"API 세션 생성 실패: {e}") from e
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """비동기 컨텍스트 매니저 종료
        
        Raises:
            ApiError: API 세션 종료 실패 시
        """
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                raise ApiError(f"API 세션 종료 실패: {e}") from e
            finally:
                self.session = None
        
    async def register_snapshot(self, data: SnapshotRequest) -> None:
        """스냅샷 등록 API 호출
        
        Args:
            data: 등록할 스냅샷 데이터
            
        Raises:
            MetadataError: 메타데이터 등록 실패 시
            ApiError: API 통신 실패 시
        """
        if not self.session:
            try:
                self.session = aiohttp.ClientSession()
            except Exception as e:
                raise ApiError(f"API 세션 생성 실패: {e}") from e
            
        try:
            async with self.session.post(
                f"{self.api_url}/snapshots",
                json=data,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    self.logger.info(f"스냅샷 등록 성공: {data['snapshot_path']}")
                    return
                else:
                    response_text = await response.text()
                    raise MetadataError(f"스냅샷 등록 실패: {response.status} - {response_text}")
                    
        except asyncio.TimeoutError as e:
            raise ApiError(f"API 요청 시간 초과: {data['snapshot_path']}") from e
        except aiohttp.ClientError as e:
            raise ApiError(f"API 요청 실패: {e}") from e
        except Exception as e:
            raise MetadataError(f"API 요청 중 오류 발생: {e}") from e 