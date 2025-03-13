import asyncio
from pathlib import Path
from src.core.api import APIClient
from src.core.snapshot import SnapshotManager
from src.core.path_info import PathInfo
from src.utils.logger import get_logger, set_file_context, clear_file_context
from dataclasses import dataclass

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

    async def process_events(self):
        """메인 이벤트 큐에서 학생별 큐로 이벤트 라우팅"""
        while True:
            event = await self.event_queue.get()
            try:
                path_info = PathInfo.from_source_path(event["path"])
                student_id = path_info.student_id
                
                # 라우팅 시점의 컨텍스트 설정
                set_file_context(
                    class_student=f"{path_info.class_div}-{path_info.student_id}"
                )
                
                if student_id not in self._student_handlers:
                    self._student_handlers[student_id] = StudentEventHandler.create()
                    asyncio.create_task(self._process_student_events(student_id))
                
                await self._student_handlers[student_id].queue.put(event)
                logger.debug(
                    f"학생 {student_id}의 큐에 이벤트 추가 - "
                    f"유형: {event['event_type']}, "
                    f"경로: {event['path']}"
                )
            except Exception as e:
                logger.error(f"이벤트 라우팅 중 오류 발생: {e}")
            finally:
                self.event_queue.task_done()
                clear_file_context()

    async def _process_student_events(self, student_id: str):
        """학생별 이벤트 처리"""
        handler = self._student_handlers[student_id]
        
        while True:
            event = await handler.queue.get()
            try:
                event_type = event["event_type"]
                file_path = event["path"]
                path_info = PathInfo.from_source_path(file_path)
                
                # 이벤트 처리 태스크의 컨텍스트 설정
                set_file_context(
                    class_student=f"{path_info.class_div}-{path_info.student_id}"
                )
                
                # 스냅샷 생성 부분만 락으로 보호
                snapshot_path = None
                async with handler.lock:
                    logger.debug(
                        f"학생 {student_id}의 스냅샷 생성 시작 - "
                        f"유형: {event_type}, "
                        f"경로: {file_path}"
                    )
                    
                    if event_type == "modified":
                        snapshot_path = await self._create_modified_snapshot(file_path)
                    else:  # deleted
                        snapshot_path = await self._create_deleted_snapshot(file_path)
                    
                    logger.debug(
                        f"학생 {student_id}의 스냅샷 생성 완료 - "
                        f"스냅샷: {snapshot_path}"
                    )
                
                # 스냅샷이 생성된 경우 API 호출을 실행
                if snapshot_path:
                    if event_type == "modified":
                        await self._send_modified_to_api(path_info, snapshot_path)
                    else:  # deleted
                        await self._send_deleted_to_api(path_info, snapshot_path)
                    
            except Exception as e:
                logger.error(f"학생 {student_id}의 이벤트 처리 중 오류: {e}")
            finally:
                handler.queue.task_done()
                clear_file_context()

    async def _create_modified_snapshot(self, file_path: str) -> str | None:
        """수정된 파일의 스냅샷 생성"""
        if not await self.snapshot_manager.has_changed(file_path):
            return None
        return await self.snapshot_manager.create_snapshot(file_path)

    async def _create_deleted_snapshot(self, file_path: str) -> str | None:
        """삭제된 파일의 스냅샷 생성"""
        return await self.snapshot_manager.create_empty_snapshot(file_path)

    async def _send_modified_to_api(self, path_info: PathInfo, snapshot_path: str):
        """수정된 파일의 스냅샷 정보를 API로 전송"""
        try:
            snapshot = Path(snapshot_path)
            await self.api_client.register_snapshot(
                class_div=path_info.class_div,
                hw_name=path_info.hw_name,
                student_id=path_info.student_id,
                filename=path_info.filename,
                timestamp=snapshot.name,
                file_size=snapshot.stat().st_size
            )
            logger.debug(f"수정된 파일 API 전송 완료 - 학생: {path_info.student_id}, 스냅샷: {snapshot_path}")
        except Exception as e:
            logger.error(f"수정된 파일 API 전송 중 오류: {e}")

    async def _send_deleted_to_api(self, path_info: PathInfo, snapshot_path: str):
        """삭제된 파일의 스냅샷 정보를 API로 전송"""
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
            logger.debug(f"삭제된 파일 API 전송 완료 - 학생: {path_info.student_id}, 스냅샷: {snapshot_path}")
        except Exception as e:
            logger.error(f"삭제된 파일 API 전송 중 오류: {e}") 