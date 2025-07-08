import asyncio
from pathlib import Path
from src.core.api import APIClient
from src.core.snapshot import SnapshotManager
from src.core.path_info import PathInfo
from src.utils.logger import get_logger, set_file_context, clear_file_context
from dataclasses import dataclass
from src.core.watchdog_handler import WatcherEvent

logger = get_logger(__name__)

@dataclass
class StudentEventHandler:
    """학생별 이벤트 처리 상태를 관리하는 클래스"""
    queue: asyncio.Queue
    lock: asyncio.Lock
    
    @classmethod
    def create(cls) -> 'StudentEventHandler':
        """새로운 핸들러 생성"""
        return cls(
            queue=asyncio.Queue(),
            lock=asyncio.Lock()
        )

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
        self._student_handlers: dict[str, StudentEventHandler] = {}

    async def route_events(self):
        """메인 이벤트 큐에서 학생별 큐로 이벤트 라우팅"""
        while True:
            event = await self.event_queue.get()
            try:
                student_id = event.path_info.student_id
                
                # 라우팅 시점의 컨텍스트 설정
                set_file_context(
                    class_student=f"{event.path_info.class_div}-{event.path_info.student_id}"
                )
                
                # 이벤트 감지 로그 추가 (상세 정보 포함)
                logger.info(
                    f"이벤트 감지됨 - 타입: {event.event_type}, "
                    f"경로: {event.source_path}, "
                )
                
                if student_id not in self._student_handlers:
                    self._student_handlers[student_id] = StudentEventHandler.create()
                    asyncio.create_task(self._process_student_events(student_id))
                
                await self._student_handlers[student_id].queue.put(event)

            except Exception as e:
                logger.error(f"Event routing failed - error: {str(e)}")
            finally:
                self.event_queue.task_done()
                clear_file_context()

    async def _process_student_events(self, student_id: str):
        """학생별 이벤트 처리"""
        handler = self._student_handlers[student_id]
        
        while True:
            event = await handler.queue.get()
            try:
                # 이벤트 처리 태스크의 컨텍스트 설정
                set_file_context(
                    class_student=f"{event.path_info.class_div}-{event.path_info.student_id}"
                )
                
                # 스냅샷 생성 부분만 락으로 보호
                snapshot_path = None
                async with handler.lock:
                    logger.debug(
                        f"Snapshot creation started - type: {event.event_type}, "
                        f"path: {event.source_path}"
                    )
                    
                    if event.event_type == "modified":
                        snapshot_path = await self._create_modified_snapshot(event.source_path)
                    else:  # deleted
                        snapshot_path = await self._create_empty_snapshot(event.source_path)
                    
                    if snapshot_path:
                        logger.debug(f"Snapshot created - path: {snapshot_path}")
                
                # 스냅샷이 생성된 경우 API 호출을 실행
                if snapshot_path:
                    if event.event_type == "modified":
                        await self._register_modified_snapshot(event.path_info, snapshot_path)
                    else:  # deleted
                        await self._register_deleted_snapshot(event.path_info, snapshot_path)
                    
            except Exception as e:
                logger.error(f"Event processing failed - error: {str(e)}")
            finally:
                handler.queue.task_done()
                clear_file_context()

    async def _create_modified_snapshot(self, file_path: str) -> str | None:
        """수정된 파일의 스냅샷 생성"""
        if not await self.snapshot_manager.has_changed(file_path):
            return None
        return await self.snapshot_manager.create_snapshot(file_path)

    async def _create_empty_snapshot(self, file_path: str) -> str | None:
        """삭제된 파일의 빈 스냅샷 생성"""
        return await self.snapshot_manager.create_empty_snapshot(file_path)

    async def _register_modified_snapshot(self, path_info: PathInfo, snapshot_path: str):
        """수정된 파일의 스냅샷 정보를 API에 등록"""
        try:
            snapshot = Path(snapshot_path)
            file_size = snapshot.stat().st_size
            await self.api_client.register_snapshot(
                class_div=path_info.class_div,
                hw_name=path_info.hw_name,
                student_id=path_info.student_id,
                filename=path_info.filename,
                timestamp=snapshot.name,
                file_size=file_size
            )
            logger.debug(
                f"API 등록 완료 - "
                f"파일: {path_info.filename}, 크기: {file_size}"
            )
        except Exception as e:
            logger.error(
                f"API 등록 실패 - "
                f"파일: {path_info.filename}, 오류: {repr(e)}"
            )

    async def _register_deleted_snapshot(self, path_info: PathInfo, snapshot_path: str):
        """삭제된 파일의 스냅샷 정보를 API에 등록"""
        try:
            snapshot = Path(snapshot_path)
            await self.api_client.register_snapshot(
                class_div=path_info.class_div,
                hw_name=path_info.hw_name,
                student_id=path_info.student_id,
                filename=path_info.filename,
                timestamp=snapshot.name,
                file_size=0
            )
        except Exception as e:
            logger.error(
                f"API 등록 실패 - "
                f"파일: {path_info.filename}, 오류: {repr(e)}"
            ) 