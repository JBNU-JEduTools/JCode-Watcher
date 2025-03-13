from src.utils.logger import get_logger
import aiohttp
from typing import Optional
from pathlib import Path

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        logger.info(f"APIClient initialized with base URL: {self.base_url}")
        
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
        
        logger.debug(f"Attempting to register snapshot: {filename}")
        logger.debug(f"Full API URL: {full_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    full_url,
                    json={"bytes": file_size}
                ) as response:
                    if response.status == 200:
                        logger.info(
                            f"Successfully registered snapshot - "
                            f"file: {filename}, size: {file_size} bytes"
                        )
                        return True
                    
                    response_text = await response.text()
                    logger.error(
                        f"Failed to register snapshot - "
                        f"status: {response.status}, "
                        f"response: {response_text}"
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(
                f"API call failed for {filename} - "
                f"error: {str(e)}"
            )
            return False 