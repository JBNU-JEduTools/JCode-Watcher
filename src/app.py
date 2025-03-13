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

class EventProcessor:
    """이벤트 처리를 담당하는 클래스"""
    
    def __init__(
        self,
        event_queue: asyncio.Queue,
        api_client: APIClient,
        snapshot_manager: SnapshotManager
    ):
        self.event_queue = event_queue
        self.api_client = api_client
        self.snapshot_manager = snapshot_manager
    
    async def process_events(self):
        """이벤트 큐 처리"""
        while True:
            event = await self.event_queue.get()
            try:
                event_type = event["event_type"]
                file_path = event["path"]
                
                if event_type == "modified":
                    await self._handle_modified(file_path)
                elif event_type == "deleted":
                    await self._handle_deleted(file_path)
                
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류 발생: {e}")
            finally:
                self.event_queue.task_done()
    
    async def _handle_modified(self, file_path: str):
        """수정된 파일 처리"""
        # 1. 파일 변경 여부 확인
        if not await self.snapshot_manager.has_changed(file_path):
            return
        
        # 2. 스냅샷 생성
        snapshot_path = await self.snapshot_manager.create_snapshot(file_path)
        if not snapshot_path:
            return
        
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
    
    async def _handle_deleted(self, file_path: str):
        """삭제된 파일 처리"""
        try:
            path_info = PathInfo.from_source_path(file_path)
            logger.info(f"파일 삭제 감지됨: {file_path}")
            
            # TODO: API 클라이언트에 delete_snapshot 메서드 추가 필요
            # await self.api_client.delete_snapshot(
            #     class_div=path_info.class_div,
            #     hw_name=path_info.hw_name,
            #     student_id=path_info.student_id,
            #     filename=path_info.filename
            # )
            
        except ValueError as e:
            logger.error(f"삭제된 파일의 경로 정보 추출 중 오류 발생: {e}")

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
    
    def stop(self):
        """파일 시스템 감시 중지"""
        self.observer.stop()
        self.observer.join()
        logger.info("파일 감시가 중지되었습니다.")
    
    async def run(self):
        """파일 감시 및 이벤트 처리 실행"""
        self.start()
        await self.event_processor.process_events()

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
        await watcher.run()
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