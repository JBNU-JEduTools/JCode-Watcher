import asyncio
import signal
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import start_http_server
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
from app.tasks import monitor_watchdog, monitor_queues, run_debouncer, run_main_pipeline

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

    # 프로메테우스 메트릭 서버 시작
    start_http_server(settings.METRICS_PORT)
    logger.info("프로메테우스 메트릭 서버 시작", port=settings.METRICS_PORT)

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
            tg.create_task(monitor_queues(raw_queue, processed_queue))
    except* Exception as eg:
        logger.critical("TaskGroup에서 하나 이상의 처리되지 않은 예외 발생. 시스템을 종료합니다.", exc_info=True)
    finally:
        await shutdown(pipeline, observer, executor)

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