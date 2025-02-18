"""
파일 시스템 감시 메인 모듈
watchdog과 asyncio를 사용하여 특정 디렉토리의 파일 변경을 감시
"""
import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer

from .config.settings import Config
from .utils.file_filter import FileFilter
from .services.metadata_service import ApiMetadataService
from .services.snapshot_service import SnapshotManager
from .storage.filesystem import FileSystemSnapshotStorage
from .utils.event_queue import EventQueue
from .utils.file_comparator import FileComparator
from .utils.logger import setup_logger
from .watchers.event_handler import FileChangeHandler
from .watchers.file_watcher import FileWatcher

# 로깅 설정
setup_logger()

async def main():
    """메인 함수"""
    loop = asyncio.get_running_loop()
    
    # 컴포넌트 초기화
    logging.info("=== 애플리케이션 시작 ===")
    logging.info(f"기본 경로: {Config.BASE_PATH}")
    logging.info(f"스냅샷 경로: {Config.SNAPSHOT_PATH}")
    
    event_queue = EventQueue(loop)
    storage = FileSystemSnapshotStorage(Path(Config.SNAPSHOT_PATH))
    comparator = FileComparator()
    metadata_service = ApiMetadataService()
    snapshot_manager = SnapshotManager(storage, comparator, metadata_service)
    file_filter = FileFilter()
    
    # 파일 감시 설정
    handler = FileChangeHandler(event_queue, file_filter)
    observer = Observer()
    file_watcher = FileWatcher(
        Path(Config.BASE_PATH),
        Config.WATCH_PATTERN,
        Config.HOMEWORK_PATTERN
    )
    
    # 감시 디렉토리 설정
    watch_dirs = file_watcher.find_watch_directories()
    if not watch_dirs:
        logging.error("감시할 디렉토리가 없습니다. 설정을 확인하세요.")
        return
        
    # 감시 시작
    for watch_dir in watch_dirs:
        observer.schedule(handler, str(watch_dir), recursive=True)
        logging.debug(f"감시자 등록: {watch_dir}")
    
    observer.start()
    logging.info("=== 파일 시스템 감시 시작 ===")
    
    try:
        # 이벤트 처리 루프
        while True:
            try:
                _, file_path = await event_queue.get_event()
                await snapshot_manager.save_snapshot(file_path)
                event_queue.task_done()
            except Exception as e:
                logging.error(f"이벤트 처리 중 오류 발생: {e}")
                event_queue.task_done()
    except KeyboardInterrupt:
        observer.stop()
        logging.info("파일 시스템 감시 중단")
    
    observer.join()
    logging.info("=== 애플리케이션 종료 ===")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("프로그램 종료")
