import asyncio
import signal
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from app.watchdog_handler import WatchdogHandler
from app.pipeline import FilemonPipeline
from app.debouncer import Debouncer
from app.snapshot import SnapshotManager
from app.sender import SnapshotSender
from app.source_path_parser import SourcePathParser
from app.source_path_filter import PathFilter
from app.config.settings import settings
from app.utils.logger import setup_logging, get_logger

logger=None

async def main():
    # 로깅 시스템 초기화
    setup_logging(
        log_file_path=settings.LOG_FILE_PATH,
        log_level=settings.LOG_LEVEL,
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT
    )
    
    # 로거 초기화 (setup_logging 이후에 호출)
    global logger
    logger = get_logger(__name__)
    logger.info("Filemon 애플리케이션 시작")
    loop = asyncio.get_running_loop()

    # 의존성 생성
    parser = SourcePathParser()
    path_filter = PathFilter()
    executor = ThreadPoolExecutor(max_workers=settings.THREAD_POOL_WORKERS, thread_name_prefix="filemon")
    raw_queue = asyncio.Queue()
    processed_queue = asyncio.Queue()
    snapshot_manager = SnapshotManager()
    snapshot_sender = SnapshotSender()
    pipeline = FilemonPipeline(executor=executor, snapshot_manager=snapshot_manager, snapshot_sender=snapshot_sender, parser=parser, path_filter=path_filter)
    debouncer = Debouncer(processed_queue=processed_queue)
    handler = WatchdogHandler(raw_queue=raw_queue, loop=loop, path_filter=path_filter)
    logger.debug("의존성 객체 생성 완료")

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
        async with asyncio.TaskGroup() as tg:
            tg.create_task(run_debouncer(debouncer, raw_queue))
            tg.create_task(run_main_pipeline(processed_queue, pipeline))
    finally:
        await shutdown(pipeline, observer, executor)

async def run_debouncer(debouncer: Debouncer, raw_queue: asyncio.Queue):
    """debouncer 실행 태스크"""
    logger.info("Debouncer 시작")
    try:
        while True:
            raw_event = await raw_queue.get()
            await debouncer.process_event(raw_event)
    except asyncio.CancelledError:
        logger.info("Debouncer 종료")
        raise
    except Exception as e:
        logger.error(f"Debouncer 오류: {e}", exc_info=True)

async def run_main_pipeline(processed_queue: asyncio.Queue, pipeline: FilemonPipeline):
    """메인 파이프라인 실행 태스크"""
    logger.info("메인 파이프라인 시작")
    try:
        while True:
            event = await processed_queue.get()
            try:
                await pipeline.process_event(event)
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류: {e}", 
                           event_type=event.event_type, 
                           src_path=event.src_path, 
                           exc_info=True)
    except asyncio.CancelledError:
        logger.info("메인 파이프라인 종료")
        raise
    except Exception as e:
        logger.error(f"메인 파이프라인 오류: {e}", exc_info=True)

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