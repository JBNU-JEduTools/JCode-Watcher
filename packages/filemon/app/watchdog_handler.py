import asyncio
from pathlib import Path
from app.utils.logger import get_logger
from watchdog.events import FileSystemEventHandler
from app.path_filter import PathFilter

logger = get_logger(__name__)

class WatchdogHandler(FileSystemEventHandler):
    
    def __init__(self, raw_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, path_filter: PathFilter):
        super().__init__()
        self.raw_queue = raw_queue
        self.loop = loop
        self.path_filter = path_filter

    def on_modified(self, event):
        try:
            if not self.path_filter.should_process_file(event.src_path):
                logger.info(f"Ignoring modified event for path due to filter: {event.src_path}")
                return
            
            self.loop.call_soon_threadsafe(
                self.raw_queue.put_nowait, event
            )
            
        except Exception as e:
            logger.error("on_modified 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, error=str(e), exc_info=True)

    def on_deleted(self, event):
        try:
            if not self.path_filter.should_process_path(event.src_path):
                logger.info(f"Ignoring deleted event for path due to filter: {event.src_path}")
                return
            
            self.loop.call_soon_threadsafe(
                self.raw_queue.put_nowait, event
            )
            
        except Exception as e:
            logger.error("on_deleted 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, error=str(e), exc_info=True)

    def on_moved(self, event):
        try:
            dest_path = getattr(event, 'dest_path', event.src_path)
            if not self.path_filter.should_process_file(dest_path):
                logger.info(f"Ignoring moved event for path due to filter: {dest_path}")
                return
            
            self.loop.call_soon_threadsafe(
                self.raw_queue.put_nowait, event
            )
            
        except Exception as e:
            logger.error("on_moved 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, 
                        dest_path=getattr(event, 'dest_path', None), 
                        error=str(e), exc_info=True)