import asyncio
from watchdog.observers import Observer
from app.debouncer import Debouncer
from app.pipeline import FilemonPipeline
from app.utils.logger import get_logger
from app.utils.metrics import watchdog_up, set_queue_size, processing_duration_seconds

logger = get_logger(__name__)

# --- Monitoring Tasks ---

async def monitor_watchdog(observer: Observer):
    """Watchdog Observer 스레드를 주기적으로 모니터링합니다."""
    logger.info("Watchdog 모니터링 시작", component="watchdog_monitor")
    while True:
        if not observer.is_alive():
            # Watchdog 스레드의 중지는 심각한 오류이므로, 예외를 발생시켜 시스템 전체를 종료시킵니다.
            raise RuntimeError("Watchdog Observer 스레드가 예기치 않게 중지되었습니다.")
        watchdog_up.set(1)
        await asyncio.sleep(10)

async def monitor_queues(raw_queue: asyncio.Queue, processed_queue: asyncio.Queue):
    """주요 큐들의 현재 사이즈를 주기적으로 측정합니다."""
    logger.info("큐 모니터링 시작", component="queue_monitor")
    while True:
        set_queue_size("raw", raw_queue.qsize())
        set_queue_size("processed", processed_queue.qsize())
        await asyncio.sleep(10)

# --- Core Worker Tasks ---

async def run_debouncer(debouncer: Debouncer, raw_queue: asyncio.Queue):
    """debouncer 실행 태스크. 오류 발생 시 TaskGroup에 의해 자동 종료됩니다."""
    logger.info("Debouncer 시작", component="debouncer")
    while True:
        raw_event = await raw_queue.get()
        with processing_duration_seconds.labels(component='debouncer').time():
            await debouncer.process_event(raw_event)

async def run_main_pipeline(processed_queue: asyncio.Queue, pipeline: FilemonPipeline):
    """메인 파이프라인 실행 태스크. 개별 이벤트 오류는 로깅 후 무시하고, 루프 자체의 오류는 TaskGroup에 의해 처리됩니다."""
    logger.info("메인 파이프라인 시작", component="pipeline")
    while True:
        event = await processed_queue.get()
        with processing_duration_seconds.labels(component='pipeline').time():
            await pipeline.process_event(event)

