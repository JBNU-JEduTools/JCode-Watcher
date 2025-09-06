import aiohttp
from typing import Optional
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import settings
from app.models.source_file_info import SourceFileInfo
from app.utils.metrics import record_api_request

logger = get_logger(__name__)


class SnapshotSender:
    """스냅샷 등록 API 클라이언트"""
    
    def __init__(self):
        self.base_url = settings.API_SERVER.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT_TOTAL)
        logger.info("API 클라이언트 초기화 완료", base_url=self.base_url)
    
    async def register_snapshot(self, source_file_info: SourceFileInfo, file_size: int) -> bool:
        """
        스냅샷 등록 API 호출
        
        Args:
            source_file_info: 소스 파일 정보
            file_size: 파일 크기 (bytes)
            
        Returns:
            bool: 등록 성공 여부
        """
        # API 엔드포인트 구성
        endpoint = f"/api/{source_file_info.class_div}/{source_file_info.hw_name}/{source_file_info.student_id}/{source_file_info.filename}/{source_file_info.timestamp}"
        full_url = f"{self.base_url}{endpoint}"
        
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    full_url,
                    json={"bytes": file_size}
                ) as response:
                    if response.status == 200:
                        logger.info("API 요청 성공", 
                                   filename=source_file_info.filename,
                                   class_div=source_file_info.class_div,
                                   hw_name=source_file_info.hw_name,
                                   student_id=source_file_info.student_id)
                        record_api_request("success")
                        return True
                    
                    response_text = await response.text()
                    logger.error("API 요청 실패",
                               filename=source_file_info.filename,
                               class_div=source_file_info.class_div,
                               hw_name=source_file_info.hw_name,
                               student_id=source_file_info.student_id,
                               status_code=response.status,
                               response_text=response_text)
                    record_api_request("failure")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error("API 오류 발생",
                       filename=source_file_info.filename,
                       class_div=source_file_info.class_div,
                       hw_name=source_file_info.hw_name,
                       student_id=source_file_info.student_id,
                       error_type="aiohttp.ClientError",
                       exc_info=True)
            record_api_request("failure")
            return False
        except Exception as e:
            logger.error("예상치 못한 API 오류",
                       filename=source_file_info.filename,
                       class_div=source_file_info.class_div,
                       hw_name=source_file_info.hw_name,
                       student_id=source_file_info.student_id,
                       error_type=type(e).__name__,
                       exc_info=True)
            record_api_request("failure")
            return False