import asyncio

import aiohttp
from app.config.settings import settings
from app.course_resolver import CourseIdResolver
from app.models.source_file_info import SourceFileInfo
from app.spool import EventSpool
from app.utils.logger import get_logger
from app.utils.metrics import record_api_request

logger = get_logger(__name__)


class SnapshotSender:
    """Persist snapshots before sending them to the transactional batch API."""

    def __init__(
        self,
        course_resolver: CourseIdResolver | None = None,
        spool_path: str | None = None,
    ):
        self.base_url = settings.API_SERVER.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT_TOTAL)
        self.course_resolver = course_resolver or CourseIdResolver()
        self.spool = EventSpool(spool_path or settings.SPOOL_PATH)
        self._flush_lock = asyncio.Lock()
        logger.info("API 클라이언트 초기화 완료", base_url=self.base_url)

    async def register_snapshot(
        self, source_file_info: SourceFileInfo, file_size: int
    ) -> bool:
        payload = {
            "event_id": str(source_file_info.event_id),
            "assignment_id": source_file_info.assignment_id,
            "student_key": source_file_info.student_id,
            "class_div": source_file_info.class_div,
            "hw_name": source_file_info.hw_name,
            "relative_path": source_file_info.filename,
            "file_size": file_size,
            "occurred_at": source_file_info.occurred_at.isoformat(),
        }
        await asyncio.to_thread(self.spool.enqueue, "snapshot", payload)
        await self.flush_once()
        return not await asyncio.to_thread(
            self.spool.contains, str(source_file_info.event_id)
        )

    async def flush_once(self) -> int:
        async with self._flush_lock:
            records = await asyncio.to_thread(
                self.spool.pending, settings.SPOOL_BATCH_SIZE
            )
            if not records:
                return 0

            events = []
            attempted_ids = []
            for record in records:
                try:
                    course_id = await self.course_resolver.resolve(
                        record.payload["class_div"]
                    )
                except Exception:
                    logger.warning(
                        "강의 식별자 확인 실패",
                        event_id=record.event_id,
                        exc_info=True,
                    )
                    continue
                events.append(
                    {
                        "type": record.event_type,
                        "payload": {**record.payload, "course_id": course_id},
                    }
                )
                attempted_ids.append(record.event_id)

            if not events:
                await asyncio.to_thread(
                    self.spool.retry_later,
                    [record.event_id for record in records],
                    settings.SPOOL_RETRY_SECONDS,
                )
                return 0

            try:
                async with (
                    aiohttp.ClientSession(timeout=self.timeout) as session,
                    session.post(
                        f"{self.base_url}/api/v2/events/batch", json={"events": events}
                    ) as response,
                ):
                    if response.status >= 400:
                        raise RuntimeError(
                            f"Watcher batch API {response.status}: "
                            f"{await response.text()}"
                        )
                    body = await response.json()
                acknowledged = {
                    str(value) for value in body.get("acknowledged_event_ids", [])
                }
                completed = [value for value in attempted_ids if value in acknowledged]
                await asyncio.to_thread(self.spool.acknowledge, completed)
                unacknowledged = [
                    value for value in attempted_ids if value not in acknowledged
                ]
                await asyncio.to_thread(
                    self.spool.retry_later,
                    unacknowledged,
                    settings.SPOOL_RETRY_SECONDS,
                )
                record_api_request("success")
                return len(completed)
            except Exception:
                logger.exception("이벤트 배치 전송 실패")
                await asyncio.to_thread(
                    self.spool.retry_later,
                    attempted_ids,
                    settings.SPOOL_RETRY_SECONDS,
                )
                record_api_request("failure")
                return 0

    async def run_retry_loop(self, started_event: asyncio.Event | None = None):
        while True:
            await self.flush_once()
            if started_event is not None:
                started_event.set()
                started_event = None
            await asyncio.sleep(settings.SPOOL_RETRY_SECONDS)
