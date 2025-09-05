import asyncio
from pathlib import Path
from app.utils.logger import get_logger
from watchdog.events import FileSystemEventHandler
from app.source_path_filter import PathFilter

logger = get_logger(__name__)

class WatchdogHandler(FileSystemEventHandler):
    
    def __init__(self, raw_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, path_filter: PathFilter):
        super().__init__()
        self.raw_queue = raw_queue
        self.loop = loop
        self.path_filter = path_filter

    def on_modified(self, event):
        try:
            if self.path_filter.is_directory(event.src_path):
                return  # 디렉토리는 조용히 무시
            
            if not self.path_filter.should_process(event.src_path):
                logger.info("필터로 인해 수정 이벤트 무시", src_path=event.src_path)
                return
            
            self.loop.call_soon_threadsafe(
                self.raw_queue.put_nowait, event
            )
            
        except Exception as e:
            logger.error("on_modified 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, exc_info=True)

    def on_deleted(self, event):
        try:
            if not self.path_filter.should_process(event.src_path):
                logger.info("필터로 인해 삭제 이벤트 무시", src_path=event.src_path)
                return
            
            self.loop.call_soon_threadsafe(
                self.raw_queue.put_nowait, event
            )
            
        except Exception as e:
            logger.error("on_deleted 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, exc_info=True)

    def on_moved(self, event):
        try:
            dest_path = getattr(event, 'dest_path', event.src_path)
            if self.path_filter.is_directory(dest_path):
                return  # 디렉토리는 조용히 무시
            
            if not self.path_filter.should_process(dest_path):
                logger.info("필터로 인해 이동 이벤트 무시", dest_path=dest_path)
                return
            
            self.loop.call_soon_threadsafe(
                self.raw_queue.put_nowait, event
            )
            
        except Exception as e:
            logger.error("on_moved 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, 
                        dest_path=getattr(event, 'dest_path', None), 
                        exc_info=True)