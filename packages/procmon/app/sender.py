import asyncio
import time
from typing import Any

import aiohttp

from app.config.settings import settings
from app.course_resolver import CourseIdResolver
from app.models.event import Event
from app.models.process_type import ProcessType
from app.spool import EventSpool
from app.utils.logger import get_logger
from app.utils.metrics import record_api_duration, record_api_request


class EventSender:
    """Persist process events before sending them to the transactional batch API."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 20,
        course_resolver: CourseIdResolver | None = None,
        spool_path: str | None = None,
    ):
        self.logger = get_logger("sender")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.course_resolver = course_resolver or CourseIdResolver()
        self.spool = EventSpool(spool_path or settings.SPOOL_PATH)
        self._flush_lock = asyncio.Lock()

    async def send_event(self, event: Event) -> bool:
        if not self._validate_event(event):
            return False
        serialized = self._serialize_event(event)
        if serialized is None:
            return False
        event_type, payload = serialized
        await asyncio.to_thread(self.spool.enqueue, event_type, payload)
        await self.flush_once()
        return not await asyncio.to_thread(self.spool.contains, str(event.event_id))

    def _validate_event(self, event: Event) -> bool:
        if not event.class_div or not event.student_id or not event.homework_dir:
            self.logger.error("필수 필드 누락: class_div, student_id, homework_dir")
            return False
        return True

    def _serialize_event(self, event: Event) -> tuple[str, dict[str, Any]] | None:
        identity = {
            "event_id": str(event.event_id),
            "assignment_id": event.assignment_id,
            "student_key": event.student_id,
            "class_div": event.class_div,
            "hw_name": event.homework_dir,
            "occurred_at": event.timestamp.isoformat(),
        }
        if event.process_type.is_execution:
            process_type = (
                "python" if event.process_type == ProcessType.PYTHON else "binary"
            )
            return "run", {
                **identity,
                "exit_code": event.exit_code,
                "cmdline": " ".join(event.args) if event.args else "",
                "cwd": event.cwd,
                "target_path": event.source_file or event.binary_path,
                "process_type": process_type,
            }
        if event.process_type.is_compilation:
            return "build", {
                **identity,
                "exit_code": event.exit_code,
                "cmdline": " ".join(event.args) if event.args else "",
                "cwd": event.cwd,
                "binary_path": event.binary_path,
                "target_path": event.source_file,
            }
        self.logger.warning("알 수 없는 이벤트 타입", event_type=str(event.process_type))
        return None

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
                    self.logger.warning(
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

            started = time.time()
            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.post(
                        f"{self.base_url}/api/v2/events/batch",
                        json={"events": events},
                        timeout=self.timeout,
                    ) as response,
                ):
                    record_api_request(str(response.status), "batch")
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
                await asyncio.to_thread(
                    self.spool.retry_later,
                    [value for value in attempted_ids if value not in acknowledged],
                    settings.SPOOL_RETRY_SECONDS,
                )
                return len(completed)
            except Exception:
                record_api_request("error", "batch")
                self.logger.exception("이벤트 배치 전송 실패")
                await asyncio.to_thread(
                    self.spool.retry_later,
                    attempted_ids,
                    settings.SPOOL_RETRY_SECONDS,
                )
                return 0
            finally:
                record_api_duration("batch", time.time() - started)

    async def run_retry_loop(self):
        while True:
            await self.flush_once()
            await asyncio.sleep(settings.SPOOL_RETRY_SECONDS)
