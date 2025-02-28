"""소스코드 처리기

파일 시스템의 소스코드 변경을 감지하고 스냅샷을 생성하여 기록합니다.
"""
import asyncio
from pathlib import Path
from datetime import datetime
from aiohttp import ClientError

from .snapshot import SnapshotStorage
from .api import ApiClient
from .utils.event_queue import EventQueue
from .utils.logger import get_logger

logger = get_logger(__name__)

class SourceCodeProcessor:
    """소스코드 처리기
    
    소스코드 파일의 변경을 감지하고 스냅샷을 생성하여 메타데이터를 기록합니다.
    """
    
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
        """이벤트 처리 실행"""
        tasks = set()  # 동시 실행 중인 태스크 추적
        
        while True:
            try:
                event_type, source_info = await self.event_queue.get_event()
                if not source_info:
                    continue
                    
                # 새로운 태스크 생성
                task = asyncio.create_task(self.process_event(event_type, source_info))
                tasks.add(task)
                task.add_done_callback(tasks.discard)  # 완료된 태스크 제거
                
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류 발생: {str(e)}", exc_info=True)

    async def process_event(self, event_type, source_info) -> None:
        """개별 이벤트 처리"""
        try:
            source_path = Path(source_info.original_path)
            logger.info(
                f"소스코드 변경 감지 "
                f"[{source_info.class_div}/{source_info.student_id}/{source_info.hw_dir}/{source_info.filename}]"
            )
            
            # 파일 변경 여부 확인
            if not await self.storage.has_file_changed(source_path, source_info):
                logger.debug(f"스냅샷 생성 중단: 변경사항 없음...")
                return
            
            # 스냅샷 생성과 API 전송을 병렬로 처리
            snapshot = await self.storage.create(source_path, source_info)
            logger.info(f"스냅샷 생성 완료...")
            
            # API 전송
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            endpoint = f"/api/{source_info.class_div}/{source_info.hw_dir}/{source_info.student_id}/{source_info.filename}/{timestamp}"
            
            await self.api_client.send_snapshot(endpoint, {"bytes": snapshot.stat().st_size})
            logger.info(f"소스코드 스냅샷 메타데이터 기록 ({snapshot.stat().st_size} bytes)...")
            
        except ClientError as e:
            logger.error(f"메타데이터 기록 실패: API 서버 오류 ({e.__class__.__name__} - {str(e)})", exc_info=False) 