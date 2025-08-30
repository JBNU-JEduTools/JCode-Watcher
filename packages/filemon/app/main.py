import asyncio
import signal
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from app.watchdog_handler import WatchdogHandler
from app.pipeline import FilemonPipeline
from app.snapshot import SnapshotManager
from app.source_path_parser import SourcePathParser
from app.path_filter import PathFilter
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    logger.info("Filemon 애플리케이션 시작")
    loop = asyncio.get_running_loop()

    # 의존성 생성
    parser = SourcePathParser()
    path_filter = PathFilter()
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="filemon")
    event_queue = asyncio.Queue()
    snapshot_manager = SnapshotManager()
    pipeline = FilemonPipeline(executor=executor, snapshot_manager=snapshot_manager)
    handler = WatchdogHandler(event_queue=event_queue, loop=loop, parser=parser, path_filter=path_filter)
    logger.debug("모든 의존성 객체 생성 완료")

    observer = Observer()
    observer.schedule(handler, str(settings.WATCH_ROOT), recursive=True)
    observer.start()
    logger.info(f"Filemon 시작됨 - 감시 경로: {settings.WATCH_ROOT}")
    logger.info(f"스냅샷 저장 경로: {settings.SNAPSHOT_BASE}")
    logger.info(f"최대 파일 크기: {settings.MAX_CAPTURABLE_FILE_SIZE} bytes")

    # asyncio 스타일의 시그널 처리(Unix)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(pipeline, observer, executor)))

    logger.info("메인 이벤트 루프 시작")
    try:
        processed_count = 0
        while True:
            event = await event_queue.get()
            try:
                await pipeline.process_event(event)
                processed_count += 1
                if processed_count % 50 == 0:  # 50개마다 로그
                    logger.info(f"총 {processed_count}개 이벤트 처리 완료")
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류: {e}", 
                           event_type=event.event_type, 
                           filename=event.source_file_info.filename, 
                           exc_info=True)
    finally:
        await shutdown(pipeline, observer, executor)

async def shutdown(pipeline, observer, executor):
    logger.info("애플리케이션 종료 시작")
    try:
        if observer:
            observer.stop()
            observer.join()
    except Exception as e:
        logger.error(f"Observer 종료 중 오류: {e}", exc_info=True)
    finally:
        if executor:
            executor.shutdown(wait=True)
        logger.info("애플리케이션 종료 완료")