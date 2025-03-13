import asyncio
from watchdog.observers import Observer
from pathlib import Path
from src.core.watchdog_handler import SourceCodeHandler
from src.core.snapshot import SnapshotManager
from src.core.api import APIClient
from src.core.event_processor import EventProcessor
from src.config.settings import (
    WATCH_PATH,
    SNAPSHOT_DIR,
    API_URL
)
from src.core.path_info import PathInfo
from src.utils.logger import get_logger
from src.utils.inotify import log_inotify_status

logger = get_logger(__name__)

class FileWatcher:
    """파일 시스템 감시를 담당하는 클래스"""
    
    def __init__(
        self,
        watch_path: Path,
        event_processor: EventProcessor,
        observer: Observer = None
    ):
        self.watch_path = watch_path
        self.event_processor = event_processor
        self.observer = observer or Observer()
        
        # 이벤트 핸들러 초기화
        self.handler = SourceCodeHandler(
            event_processor.event_queue,
            asyncio.get_event_loop()
        )

    def start(self):
        """파일 시스템 감시 시작"""
        if not self.watch_path.exists():
            logger.error(f"감시할 경로가 존재하지 않습니다: {self.watch_path}")
            raise FileNotFoundError(f"경로를 찾을 수 없습니다: {self.watch_path}")

        self.observer.schedule(
            self.handler, 
            str(self.watch_path), 
            recursive=True
        )
        self.observer.daemon = True
        self.observer.start()
        logger.info(f"파일 감시 시작됨: {self.watch_path}")
        
        # inotify 상태 로깅
        log_inotify_status()
    
    def stop(self):
        """파일 시스템 감시 중지"""
        self.observer.stop()
        self.observer.join()
        logger.info("파일 감시가 중지되었습니다.")

async def main():
    # 컴포넌트 초기화
    event_queue = asyncio.Queue()
    api_client = APIClient(API_URL)
    snapshot_manager = SnapshotManager(str(SNAPSHOT_DIR))
    
    # 이벤트 프로세서 초기화
    event_processor = EventProcessor(
        event_queue=event_queue,
        api_client=api_client,
        snapshot_manager=snapshot_manager
    )
    
    # 파일 와쳐 초기화
    watcher = FileWatcher(
        watch_path=WATCH_PATH,
        event_processor=event_processor
    )
    
    try:
        logger.info(f"파일 감시 시스템이 시작되었습니다. (감시 경로: {WATCH_PATH})")
        # 파일 감시 시작
        watcher.start()
        # 이벤트 처리 시작
        await event_processor.route_events()
    except KeyboardInterrupt:
        logger.info("프로그램 종료 요청됨")
        watcher.stop()
    except FileNotFoundError:
        logger.error(f"감시 디렉토리를 찾을 수 없습니다: {WATCH_PATH}")
        raise
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")
        raise
    finally:
        logger.info("파일 감시 시스템이 종료되었습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 