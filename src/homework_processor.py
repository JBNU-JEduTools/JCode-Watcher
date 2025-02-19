"""과제 처리기

파일 시스템 이벤트를 처리하고 스냅샷을 생성합니다.
"""
import asyncio
import logging
from pathlib import Path
from aiohttp import ClientError

from .snapshot import SnapshotStorage
from .api import ApiClient
from .utils.event_queue import EventQueue

logger = logging.getLogger(__name__)

class HomeworkProcessor:
    """과제 처리기"""
    
    def __init__(self, event_queue: EventQueue, storage: SnapshotStorage, api_client: ApiClient):
        self.event_queue = event_queue
        self.storage = storage
        self.api_client = api_client
        
    async def run(self) -> None:
        """이벤트 처리 실행"""
        while True:
            try:
                event_type, homework_info = await self.event_queue.get_event()
                if not homework_info:
                    continue
                    
                source_path = Path(homework_info.original_path)
                logger.debug(f"과제 파일 이벤트 수신: {source_path}")
                
                # 스냅샷 생성 및 API 전송
                snapshot = await self.storage.create(source_path, homework_info)
                if snapshot:
                    snapshot_data = {
                        "class_div": homework_info.class_div,
                        "homework_dir": homework_info.hw_dir,
                        "student_id": homework_info.student_id,
                        "filename": homework_info.filename,
                        "original_path": str(source_path),
                        "snapshot_path": str(snapshot)
                    }
                    await self.api_client.send_snapshot(snapshot_data)
                    logger.info(f"스냅샷 생성 및 전송 완료: {source_path}")
            except ClientError:
                logger.warning("API 서버 연결 실패")