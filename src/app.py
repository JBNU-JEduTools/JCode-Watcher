import asyncio
from watchdog.observers import Observer
from pathlib import Path
from src.core.handler import SourceCodeHandler
from src.core.snapshot import SnapshotManager
from src.core.api import APIClient
from src.config.settings import (
    WATCH_PATH,
    SNAPSHOT_DIR,
    API_URL
)
from src.core.path_info import PathInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FileWatcher:
    def __init__(self):
        self.watch_path = WATCH_PATH
        self.event_queue = asyncio.Queue()
        self.observer = Observer()
        self.loop = asyncio.get_event_loop()
        self.handler = SourceCodeHandler(self.event_queue, self.loop)
        
        # 컴포넌트 초기화
        self.api_client = APIClient(API_URL)
        self.snapshot_manager = SnapshotManager(str(SNAPSHOT_DIR))

    def start_watching(self):
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

    async def process_events(self):
        while True:
            event = await self.event_queue.get()
            try:
                file_path = event["path"]
                
                # 1. 파일 변경 여부 확인
                if not await self.snapshot_manager.has_changed(file_path):
                    continue
                
                # 2. 스냅샷 생성
                snapshot_path = await self.snapshot_manager.create_snapshot(file_path)
                if not snapshot_path:
                    continue
                
                # 3. 경로 정보 추출 및 API 호출
                try:
                    path_info = PathInfo.from_source_path(file_path)
                    snapshot = Path(snapshot_path)
                    
                    await self.api_client.register_snapshot(
                        class_div=path_info.class_div,
                        hw_name=path_info.hw_name,
                        student_id=path_info.student_id,
                        filename=path_info.filename,
                        timestamp=snapshot.name,
                        file_size=snapshot.stat().st_size
                    )
                    
                except ValueError as e:
                    logger.error(f"경로 정보 추출 중 오류 발생: {e}")
                    continue
                
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류 발생: {e}")
            finally:
                self.event_queue.task_done()

async def main():
    watcher = FileWatcher()
    
    try:
        watcher.start_watching()
        logger.info(f"파일 감시 시스템이 시작되었습니다. (감시 경로: {WATCH_PATH})")
        await watcher.process_events()
    except KeyboardInterrupt:
        logger.info("프로그램 종료 요청됨")
        watcher.observer.stop()
        watcher.observer.join()
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