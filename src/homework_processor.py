"""과제 처리기

과제 파일 변경을 감지하고 스냅샷을 생성하는 메인 처리 흐름을 관리합니다.
"""
import os
from datetime import datetime
from pathlib import Path
import logging
import asyncio
from aiohttp import ClientError

from .snapshot import SnapshotStorage
from .api import ApiClient
from .utils.event_queue import EventQueue

logger = logging.getLogger(__name__)

class HomeworkProcessor:
    """과제 처리기"""
    
    def __init__(self, event_queue: EventQueue, storage: SnapshotStorage, api_client: ApiClient):
        """
        Args:
            event_queue: 이벤트 큐
            storage: 스냅샷 저장소
            api_client: API 클라이언트
        """
        self.event_queue = event_queue
        self.storage = storage
        self.api_client = api_client
        
    async def run(self) -> None:
        """이벤트 처리 루프 실행"""
        while True:
            try:
                await self._process_single_event()
            except ClientError as e:
                logger.warning(f"API 서버 연결 실패 (5초 후 재시도): {str(e)}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"처리 중 오류 발생: {str(e)}")
                
    async def _process_single_event(self) -> None:
        """단일 과제 처리"""
        # 이벤트 대기
        event_type, homework_info = await self.event_queue.get_event()
        logger.debug(f"이벤트 수신: {homework_info.filename} ({event_type})")
        
        # 스냅샷 생성
        snapshot_path = await self.storage.create(homework_info.original_path, homework_info)
        if not snapshot_path:
            return
            
        logger.info(f"스냅샷 생성: {homework_info.filename} -> {snapshot_path.name}")
            
        # API 서버에 등록
        await self.api_client.register_snapshot({
            "class_div": homework_info.class_div,
            "homework_dir": homework_info.hw_dir,
            "student_id": homework_info.student_id,
            "filename": homework_info.filename,
            "original_path": homework_info.original_path,
            "snapshot_path": str(snapshot_path),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "file_size": Path(homework_info.original_path).stat().st_size
        }) 