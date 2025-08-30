import asyncio
import os
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import settings
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo
from app.source_path_parser import SourcePathParser
from app.path_filter import PathFilter

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

class WatchdogHandler(FileSystemEventHandler):
    
    def __init__(self, event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, parser: SourcePathParser, path_filter: PathFilter):
        super().__init__()
        self.event_queue = event_queue
        self.loop = loop
        self.parser = parser
        self.path_filter = path_filter


    def on_modified(self, event):
        try:
            # 처리 대상 파일인지 확인
            if not self.path_filter.should_process_file(event.src_path):
                return
                
            file_size = os.path.getsize(event.src_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                logger.warning("파일 크기 초과", src_path=event.src_path, 
                             file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                return
            
            # 파일 경로 파싱
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            watcher_event = FilemonEvent.from_components(event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
            
        except OSError as e:
            logger.debug("OSError 발생 - 처리 중단", src_path=event.src_path, error=str(e))
            return
        except Exception as e:
            logger.error("on_modified 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, error=str(e), exc_info=True)

    def on_deleted(self, event):
        try:
            # 처리 대상 파일인지 확인 (삭제는 파일 존재하지 않으므로 경로만으로 확인)
            if not self.path_filter.should_process_path(event.src_path):
                return
                
            # 파일 경로 파싱
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            watcher_event = FilemonEvent.from_components(event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
            
        except Exception as e:
            logger.error("on_deleted 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, error=str(e), exc_info=True)


    def on_moved(self, event):
        """파일 이름 변경 이벤트를 삭제 및 수정 이벤트로 처리"""
        try:
            # 1. 이전 파일에 대한 삭제 이벤트 처리
            delete_event = FileSystemEvent(event.src_path)
            delete_event.event_type = "deleted"
            
            parsed_data = self.parser.parse(Path(delete_event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(delete_event.src_path))
            delete_event = FilemonEvent.from_components(delete_event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, delete_event
            )
            
            # 2. 새 파일에 대한 수정 이벤트 처리
            dest_path = getattr(event, 'dest_path', None)
            if not dest_path:
                logger.warning("이동된 파일의 dest_path 속성이 없음", src_path=event.src_path)
                return
                
            if not os.path.exists(dest_path):
                logger.warning("이동된 파일이 존재하지 않음", src_path=event.src_path, dest_path=dest_path)
                return
            
            # 이동된 파일이 처리 대상인지 확인
            if not self.path_filter.should_process_file(dest_path):
                return
                
            file_size = os.path.getsize(dest_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                logger.warning("이동된 파일 크기 초과", dest_path=dest_path, 
                             file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                return
                
            # dest_path를 source_path로 사용하여 새로운 이벤트 생성
            modify_event = FileSystemEvent(dest_path)
            modify_event.event_type = "modified"
            
            parsed_data = self.parser.parse(Path(modify_event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(modify_event.src_path))
            modify_event = FilemonEvent.from_components(modify_event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, modify_event
            )
            
        except OSError as e:
            logger.debug("이동 이벤트 처리 중 OSError 발생 - 처리 중단", 
                        src_path=event.src_path, 
                        dest_path=getattr(event, 'dest_path', None), 
                        error=str(e))
            return
        except Exception as e:
            logger.error("on_moved 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, 
                        dest_path=getattr(event, 'dest_path', None), 
                        error=str(e), exc_info=True)