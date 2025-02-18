"""애플리케이션 핵심 로직"""
import asyncio
import signal
from pathlib import Path
from typing import Callable, Awaitable
from watchdog.observers import Observer

from .config.settings import Config
from .utils.file_filter import FileFilter
from .services.metadata_service import ApiMetadataService
from .services.snapshot_service import SnapshotManager
from .storage.filesystem import FileSystemSnapshotStorage
from .utils.event_queue import EventQueue
from .utils.file_comparator import FileComparator
from .utils.logger import get_logger
from .watchers.event_handler import FileChangeHandler
from .watchers.file_watcher import FileWatcher
from .exceptions import (
    WatcherError, ApiError, MetadataError, 
    StorageError, QueueError, WatcherSetupError
)


class SignalHandler:
    """시그널 처리 클래스"""
    
    def __init__(self, shutdown_handler: Callable[[], Awaitable[None]]):
        """
        Args:
            shutdown_handler: 종료 처리를 위한 비동기 콜백 함수
        """
        self.logger = get_logger(self.__class__.__name__)
        self.shutdown_handler = shutdown_handler
        
    def setup(self, loop: asyncio.AbstractEventLoop) -> None:
        """시그널 핸들러 설정
        
        Args:
            loop: 이벤트 루프
        """
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_signal(s))
            )
            self.logger.debug(f"시그널 핸들러 등록: {sig.name}")
            
    async def _handle_signal(self, sig: signal.Signals) -> None:
        """시그널 처리
        
        Args:
            sig: 수신된 시그널
        """
        self.logger.info(f"시그널 수신: {sig.name}")
        try:
            await self.shutdown_handler()
        except Exception as e:
            self.logger.error(f"종료 처리 중 오류 발생: {e}")
            raise


class Application:
    """파일 감시 애플리케이션"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.loop = asyncio.get_running_loop()
        
        try:
            # 컴포넌트 초기화
            self.event_queue = EventQueue(self.loop)
            self.storage = FileSystemSnapshotStorage(Path(Config.SNAPSHOT_PATH))
            self.comparator = FileComparator()
            self.metadata_service = ApiMetadataService()
            self.snapshot_manager = SnapshotManager(self.storage, self.comparator, self.metadata_service)
            self.file_filter = FileFilter()
            
            # 파일 감시 설정
            self.handler = FileChangeHandler(self.event_queue, self.file_filter)
            self.observer = Observer()
            self.file_watcher = FileWatcher(
                Path(Config.BASE_PATH),
                Config.WATCH_PATTERN,
                Config.HOMEWORK_PATTERN
            )
            
            # 시그널 핸들러 설정
            self.signal_handler = SignalHandler(self.shutdown)
            self.signal_handler.setup(self.loop)
            
        except Exception as e:
            raise WatcherSetupError(f"애플리케이션 초기화 실패: {e}") from e
        
    async def setup(self) -> bool:
        """애플리케이션 설정"""
        self.logger.info("=== 애플리케이션 시작 ===")
        self.logger.info(f"기본 경로: {Config.BASE_PATH}")
        self.logger.info(f"스냅샷 경로: {Config.SNAPSHOT_PATH}")
        
        try:
            # 감시 디렉토리 설정
            watch_dirs = self.file_watcher.find_watch_directories()
            if not watch_dirs:
                raise WatcherSetupError("감시할 디렉토리가 없습니다. 설정을 확인하세요.")
                
            # 감시 시작
            for watch_dir in watch_dirs:
                self.observer.schedule(self.handler, str(watch_dir), recursive=True)
                self.logger.debug(f"감시자 등록: {watch_dir}")
                
            return True
            
        except WatcherError:
            raise
        except Exception as e:
            raise WatcherSetupError(f"애플리케이션 설정 실패: {e}") from e
        
    async def start(self) -> None:
        """애플리케이션 실행"""
        try:
            self.observer.start()
            self.logger.info("=== 파일 시스템 감시 시작 ===")
            
            while True:
                try:
                    _, file_path = await self.event_queue.get_event()
                    await self.snapshot_manager.save_snapshot(file_path)
                except asyncio.CancelledError:
                    break
                except (ApiError, MetadataError, StorageError, QueueError) as e:
                    self.logger.error(f"이벤트 처리 중 오류 발생: {e}")
                except Exception as e:
                    self.logger.error(f"예기치 않은 오류 발생: {e}")
                    
        except Exception as e:
            raise WatcherError(f"애플리케이션 실행 중 오류 발생: {e}") from e
                
    async def shutdown(self) -> None:
        """애플리케이션 종료"""
        self.logger.info("애플리케이션 종료 시작")
        
        try:
            self.observer.stop()
            
            try:
                await self.event_queue.drain()
            except QueueError as e:
                self.logger.warning(f"이벤트 큐 드레인 실패: {e}")
            
            self.observer.join()
            
            # 실행 중인 모든 태스크 취소
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            [task.cancel() for task in tasks]
            
            self.logger.info(f"{len(tasks)}개의 태스크 취소 중...")
            await asyncio.gather(*tasks, return_exceptions=True)
            
            self.loop.stop()
            self.logger.info("=== 애플리케이션 종료 ===")
            
        except Exception as e:
            raise WatcherError(f"애플리케이션 종료 중 오류 발생: {e}") from e 