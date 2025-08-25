import asyncio
from watchdog.observers import Observer
from pathlib import Path
from old.core.watchdog_handler import WatchdogHandler
from old.core.snapshot import SnapshotManager
from old.core.api import APIClient
from old.core.event_processor import EventProcessor
from old.metrics.prometheus import MetricsManager
from old.config.settings import (
    WATCH_PATH,
    SNAPSHOT_DIR,
    API_URL
)
from old.core.path_info import PathInfo
from old.utils.logger import get_logger
from old.utils.inotify import log_inotify_status

logger = get_logger(__name__)

class Application:
    """파일 시스템 감시 및 이벤트 처리를 담당하는 애플리케이션 클래스"""
    
    def __init__(
        self,
        watch_path: Path,
        snapshot_dir: Path,
        api_url: str,
        observer: Observer = None
    ):
        self.watch_path = watch_path
        self.observer = observer or Observer()
        
        # 컴포넌트 초기화
        self.event_queue = asyncio.Queue()
        self.api_client = APIClient(api_url)
        self.snapshot_manager = SnapshotManager(str(snapshot_dir))
        self.metrics_manager = MetricsManager()
        
        # 이벤트 프로세서 초기화
        self.event_processor = EventProcessor(
            event_queue=self.event_queue,
            api_client=self.api_client,
            snapshot_manager=self.snapshot_manager
        )
        
        # 이벤트 핸들러 초기화
        self.handler = WatchdogHandler(
            self.event_queue,
            asyncio.get_event_loop(),
            base_path=str(self.watch_path)
        )

    def start_watching(self):
        """파일 시스템 감시 시작"""
        if not self.watch_path.exists():
            logger.error(f"감시 경로 없음 - 경로: {self.watch_path}")
            raise FileNotFoundError(f"경로 없음: {self.watch_path}")

        self.observer.schedule(
            self.handler, 
            str(self.watch_path), 
            recursive=True
        )
        self.observer.daemon = True
        self.observer.start()
        logger.info(f"감시 시작 - 경로: {self.watch_path}")
        
        # inotify 상태 로깅
        log_inotify_status()
    
    def stop_watching(self):
        """파일 시스템 감시 중지"""
        self.observer.stop()
        self.observer.join()
        logger.info("감시 중지")

    async def run(self):
        """애플리케이션 실행"""
        try:
            logger.info(f"시스템 시작 - 감시 경로: {self.watch_path}")
            self.metrics_manager.start_server()
            self.start_watching()
            await self.event_processor.route_events()
            
        except KeyboardInterrupt:
            logger.info("종료 요청")
            self.stop_watching()
        except FileNotFoundError:
            logger.error(f"감시 디렉토리 없음 - 경로: {self.watch_path}")
            raise
        except Exception as e:
            logger.error(f"예상치 못한 오류 - 내용: {str(e)}")
            raise
        finally:
            logger.info("시스템 종료")


async def main():
    app = Application(
        watch_path=WATCH_PATH,
        snapshot_dir=SNAPSHOT_DIR,
        api_url=API_URL
    )    
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())