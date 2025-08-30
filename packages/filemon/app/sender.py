import aiohttp
from datetime import datetime
from typing import Optional
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import settings
from app.models.source_file_info import SourceFileInfo

logger = get_logger(__name__)


class SnapshotSender:
    """스냅샷 등록 API 클라이언트"""
    
    def __init__(self):
        self.base_url = settings.API_SERVER.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT_TOTAL)
        logger.info(f"API 클라이언트 초기화 완료 - 주소: {self.base_url}")
    
    async def register_snapshot(self, source_file_info: SourceFileInfo, file_size: int) -> bool:
        """
        스냅샷 등록 API 호출
        
        Args:
            source_file_info: 소스 파일 정보
            file_size: 파일 크기 (bytes)
            
        Returns:
            bool: 등록 성공 여부
        """
        # 현재 시간을 타임스탬프로 생성 (YYYYMMDD_HHMMSS 형식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # API 엔드포인트 구성
        endpoint = f"/api/{source_file_info.class_div}/{source_file_info.hw_name}/{source_file_info.student_id}/{source_file_info.filename}/{timestamp}"
        full_url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"API 요청 시작 - 파일: {source_file_info.filename}")
        logger.debug(f"API 엔드포인트 - 주소: {full_url}")
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    full_url,
                    json={"bytes": file_size}
                ) as response:
                    if response.status == 200:
                        logger.info(f"API 요청 성공 - 파일: {source_file_info.filename}")
                        return True
                    
                    response_text = await response.text()
                    logger.error(
                        f"API 요청 실패 - "
                        f"파일: {source_file_info.filename}, 상태: {response.status}, "
                        f"응답: {response_text}"
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(
                f"API 오류 발생 - "
                f"파일: {source_file_info.filename}, 내용: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"예상치 못한 API 오류 - "
                f"파일: {source_file_info.filename}, 내용: {str(e)}"
            )
            return False