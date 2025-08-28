import aiohttp
from typing import Optional
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

# API 타임아웃 설정 (초)



class SnapshotSender:
    """스냅샷 등록 API 클라이언트"""
    
    def __init__(self):
        self.base_url = settings.API_SERVER.rstrip('/')
        logger.info(f"API 클라이언트 초기화 완료 - 주소: {self.base_url}")
        
    async def register_snapshot(self, 
        class_div: str,
        hw_name: str,
        student_id: str,
        filename: str,
        timestamp: str,
        file_size: int
    ) -> bool:
        """
        스냅샷 등록 API 호출
        
        Args:
            class_div: 과목-분반 (예: os-1)
            hw_name: 과제명 (예: hw1)
            student_id: 학번
            filename: 파일명 (예: src@app@test.py)
            timestamp: 타임스탬프 (예: 20240320_153000)
            file_size: 파일 크기 (bytes)
            
        Returns:
            bool: 등록 성공 여부
        """
        endpoint = f"/api/{class_div}/{hw_name}/{student_id}/{filename}/{timestamp}"
        full_url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"API 요청 시작 - 파일: {filename}")
        logger.debug(f"API 엔드포인트 - 주소: {full_url}")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=settings.API_TIMEOUT_TOTAL)) as session:
                async with session.post(
                    full_url,
                    json={"bytes": file_size}
                ) as response:
                    if response.status == 200:
                        logger.info(f"API 요청 성공 - 파일: {filename}")
                        return True
                    
                    response_text = await response.text()
                    logger.error(
                        f"API 요청 실패 - "
                        f"파일: {filename}, 상태: {response.status}, "
                        f"응답: {response_text}"
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(
                f"API 오류 발생 - "
                f"파일: {filename}, 내용: {str(e)}"
            )
            return False