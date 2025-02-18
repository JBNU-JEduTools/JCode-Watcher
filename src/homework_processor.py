"""과제 처리기

과제 파일 변경을 감지하고 스냅샷을 생성하는 메인 처리 흐름을 관리합니다.
"""
from datetime import datetime
from pathlib import Path

from .snapshot import SnapshotStorage, SnapshotInfo
from .api import ApiClient
from .homework_handler import HomeworkHandler
from .utils.event_queue import EventQueue
from .utils.logger import get_logger

logger = get_logger(__name__)

class HomeworkProcessor:
    """과제 처리기
    
    과제 파일 변경 감지부터 스냅샷 생성, API 등록까지의 전체 처리 흐름을 관리합니다.
    """
    
    def __init__(self, event_queue: EventQueue, handler: HomeworkHandler,
                 storage: SnapshotStorage, api_client: ApiClient):
        """
        Args:
            event_queue: 이벤트 큐
            handler: 과제 파일 이벤트 처리기
            storage: 스냅샷 저장소
            api_client: API 클라이언트
        """
        self.event_queue = event_queue
        self.handler = handler
        self.storage = storage
        self.api_client = api_client
        
    async def process(self) -> None:
        """과제 처리 루프 실행"""
        while True:
            # 이벤트 대기
            event_type, file_path = await self.event_queue.get_event()
            
            # 경로 정보 파싱
            if not (path_info := self.handler.path_manager.parse_path(file_path)):
                continue
                
            # 스냅샷 생성
            if not (snapshot_path := await self.storage.create(file_path, path_info)):
                continue
                
            # API 서버에 등록
            info = SnapshotInfo(*path_info)
            await self.api_client.register_snapshot({
                "class_div": info.class_div,
                "homework_dir": info.hw_dir,
                "student_id": info.student_id,
                "filename": info.filename,
                "original_path": info.original_path,
                "snapshot_path": str(snapshot_path),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "file_size": Path(file_path).stat().st_size
            }) 