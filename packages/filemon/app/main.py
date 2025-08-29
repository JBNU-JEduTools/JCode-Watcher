import asyncio
import signal
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from app.watchdog_handler import WatchdogHandler
from app.pipeline import FilemonPipeline
from app.snapshot import SnapshotManager
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    loop = asyncio.get_running_loop()

    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="filemon")
    event_queue = asyncio.Queue()
    snapshot_manager = SnapshotManager()
    pipeline = FilemonPipeline(executor=executor, snapshot_manager=snapshot_manager)

    handler = WatchdogHandler(event_queue=event_queue, loop=loop)

    observer = Observer()
    observer.schedule(handler, str(settings.WATCH_ROOT), recursive=True)
    observer.start()
    logger.info(f"Filemon 시작됨 - 감시 경로: {settings.WATCH_ROOT}")

    # asyncio 스타일의 시그널 처리(Unix)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(pipeline, observer, executor)))

    try:
        while True:
            event = await event_queue.get()
            try:
                await pipeline.process_event(event)
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류: {e}")
    finally:
        await shutdown(pipeline, observer, executor)

async def shutdown(pipeline, observer, executor):
    logger.info("애플리케이션 종료 시작")
    try:
        if observer:
            observer.stop()
            observer.join()
    finally:
        if executor:
            executor.shutdown(wait=True)
        logger.info("애플리케이션 종료 완료")