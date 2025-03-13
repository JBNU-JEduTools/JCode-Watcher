import asyncio
from pathlib import Path
from src.core.api import APIClient
from src.core.snapshot import SnapshotManager
from src.core.path_info import PathInfo
from src.utils.logger import get_logger, set_file_context, clear_file_context

logger = get_logger(__name__)

class EventProcessor:
    """이벤트 처리를 담당하는 클래스"""
    
    def __init__(
        self,
        event_queue: asyncio.Queue,
        api_client: APIClient,
        snapshot_manager: SnapshotManager
    ):
        self.event_queue = event_queue
        self.api_client = api_client
        self.snapshot_manager = snapshot_manager
    
    async def process_events(self):
        """이벤트 큐 처리"""
        while True:
            event = await self.event_queue.get()
            try:
                event_type = event["event_type"]
                file_path = event["path"]
                
                logger.debug(
                    f"이벤트 큐에서 이벤트 수신 - "
                    f"유형: {event_type}, "
                    f"경로: {file_path}"
                )
                
                if event_type == "modified":
                    asyncio.create_task(self._handle_modified(file_path))
                elif event_type == "deleted":
                    asyncio.create_task(self._handle_deleted(file_path))
                
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류 발생: {e}")
            finally:
                self.event_queue.task_done()
    
    async def _handle_modified(self, file_path: str):
        """수정된 파일 처리"""
        try:
            # 컨텍스트 설정
            path_info = PathInfo.from_source_path(file_path)
            set_file_context(
                class_student=f"{path_info.class_div}-{path_info.student_id}"
            )
            
            # 1. 파일 변경 여부 확인
            if not await self.snapshot_manager.has_changed(file_path):
                return
            
            # 2. 스냅샷 생성
            snapshot_path = await self.snapshot_manager.create_snapshot(file_path)
            if not snapshot_path:
                return
            
            # 3. 경로 정보 추출 및 API 호출
            snapshot = Path(snapshot_path)
            
            await self.api_client.register_snapshot(
                class_div=path_info.class_div,
                hw_name=path_info.hw_name,
                student_id=path_info.student_id,
                filename=path_info.filename,
                timestamp=snapshot.name,
                file_size=snapshot.stat().st_size
            )
            
        except ValueError as e:
            logger.error(f"경로 정보 추출 중 오류 발생: {e}")
        finally:
            # 컨텍스트 초기화
            clear_file_context()
    
    async def _handle_deleted(self, file_path: str):
        """삭제된 파일 처리"""
        try:
            # 컨텍스트 설정
            path_info = PathInfo.from_source_path(file_path)
            set_file_context(
                class_student=f"{path_info.class_div}-{path_info.student_id}"
            )
            
            logger.info(f"파일 삭제 감지됨: {file_path}")
            
            # 0바이트 스냅샷 생성
            snapshot_path = await self.snapshot_manager.create_empty_snapshot(file_path)
            if not snapshot_path:
                logger.error("0바이트 스냅샷 생성 실패")
                return
                
            snapshot = Path(snapshot_path)
            
            # API 호출 - 0바이트 스냅샷 등록
            await self.api_client.register_snapshot(
                class_div=path_info.class_div,
                hw_name=path_info.hw_name,
                student_id=path_info.student_id,
                filename=path_info.filename,
                timestamp=snapshot.name,
                file_size=0
            )
            
        except ValueError as e:
            logger.error(f"삭제된 파일의 경로 정보 추출 중 오류 발생: {e}")
        finally:
            # 컨텍스트 초기화
            clear_file_context() 