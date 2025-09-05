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
from app.utils.metrics import watchdog_up

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
    logger.info("Filemon 애플리케이션 시작",
               log_level=settings.LOG_LEVEL,
               log_file=settings.LOG_FILE_PATH)
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
    logger.debug("의존성 객체 생성 완료",
               thread_pool_workers=settings.THREAD_POOL_WORKERS)

    observer = Observer()
    observer.schedule(handler, str(settings.WATCH_ROOT), recursive=True)
    observer.start()
    logger.info("Filemon 시작 완료",
               watch_root=str(settings.WATCH_ROOT),
               snapshot_base=str(settings.SNAPSHOT_BASE),
               max_file_size=settings.MAX_CAPTURABLE_FILE_SIZE,
               api_server=settings.API_SERVER)

    # asyncio 스타일의 시그널 처리(Unix)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(pipeline, observer, executor)))

    logger.info("메인 이벤트 루프 시작")
    
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(run_debouncer(debouncer, raw_queue))
            tg.create_task(run_main_pipeline(processed_queue, pipeline))
            tg.create_task(monitor_watchdog(observer))
    except* Exception as eg:
        logger.critical("TaskGroup에서 하나 이상의 처리되지 않은 예외 발생. 시스템을 종료합니다.", exc_info=True)
    finally:
        await shutdown(pipeline, observer, executor)

async def run_debouncer(debouncer: Debouncer, raw_queue: asyncio.Queue):
    """debouncer 실행 태스크. 오류 발생 시 TaskGroup에 의해 자동 종료됩니다."""
    logger.info("Debouncer 시작", component="debouncer")
    while True:
        raw_event = await raw_queue.get()
        await debouncer.process_event(raw_event)

async def run_main_pipeline(processed_queue: asyncio.Queue, pipeline: FilemonPipeline):
    """메인 파이프라인 실행 태스크. 개별 이벤트 오류는 로깅 후 무시하고, 루프 자체의 오류는 TaskGroup에 의해 처리됩니다."""
    logger.info("메인 파이프라인 시작", component="pipeline")
    while True:
        event = await processed_queue.get()
        await pipeline.process_event(event)

async def monitor_watchdog(observer: Observer):
    """Watchdog Observer 스레드를 주기적으로 모니터링합니다."""
    logger.info("Watchdog 모니터링 시작", component="watchdog_monitor")
    while True:
        if not observer.is_alive():
            # Watchdog 스레드의 중지는 심각한 오류이므로, 예외를 발생시켜 시스템 전체를 종료시킵니다.
            raise RuntimeError("Watchdog Observer 스레드가 예기치 않게 중지되었습니다.")
        watchdog_up.set(1)
        await asyncio.sleep(10)

async def shutdown(pipeline, observer, executor):
    logger.info("애플리케이션 종료 시작", component="shutdown")
    try:
        if observer:
            observer.stop()
            observer.join()
    except Exception as e:
        logger.error("Observer 종료 중 오류",
                   component="shutdown",
                   error_type=type(e).__name__,
                   exc_info=True)
    finally:
        if executor:
            executor.shutdown(wait=True)
        logger.info("애플리케이션 종료 완료", component="shutdown")