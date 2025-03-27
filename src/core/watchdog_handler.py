import asyncio
import os
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from src.utils.logger import get_logger
from watchdog.events import RegexMatchingEventHandler, FileSystemEvent
from src.config.settings import (
    MAX_FILE_SIZE,
    SOURCE_PATTERNS,
    IGNORE_PATTERNS
)
from src.core.path_info import PathInfo

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

@dataclass
class WatcherEvent:
    """파일 시스템 이벤트 정보를 담는 클래스"""
    # 이벤트 기본 정보
    event_type: str
    source_path: str
    dest_path: str | None  # moved 이벤트의 경우에만 사용
    timestamp: datetime
    
    # 경로 정보
    path_info: PathInfo
    
    @classmethod
    def from_watchdog_event(cls, event: FileSystemEvent, base_path: str = '/watcher/codes') -> 'WatcherEvent':
        """watchdog 이벤트로부터 WatcherEvent 생성"""
        source_path = event.src_path
        path_info = PathInfo.from_source_path(source_path, base_path=base_path)
        
        # moved 이벤트가 아닌 경우 dest_path를 None으로 설정
        dest_path = getattr(event, 'dest_path', '') if event.event_type == 'moved' else None
        
        return cls(
            event_type=event.event_type,
            source_path=source_path,
            dest_path=dest_path,
            timestamp=datetime.now(),
            path_info=path_info
        )

class WatchdogHandler(RegexMatchingEventHandler):
    def __init__(self, event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, base_path: str = '/watcher/codes'):
        super().__init__(
            regexes=SOURCE_PATTERNS,
            ignore_regexes=IGNORE_PATTERNS,
            ignore_directories=True,
            case_sensitive=False
        )
        self.event_queue = event_queue
        self.loop = loop
        self.base_path = base_path

    def on_modified(self, event):
        try:
            if os.path.getsize(event.src_path) > MAX_FILE_SIZE:
                logger.warning(f"파일 크기 초과 - 경로: {event.src_path}, 크기: {os.path.getsize(event.src_path)}B")
                return
            
            watcher_event = WatcherEvent.from_watchdog_event(event, base_path=self.base_path)
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
        except OSError:
            return
        except Exception as e:
            logger.error(f"on_modified 처리 중 오류 발생: {str(e)}")

    def on_deleted(self, event):
        try:
            watcher_event = WatcherEvent.from_watchdog_event(event, base_path=self.base_path)
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
        except Exception as e:
            logger.error(f"on_deleted 처리 중 오류 발생: {str(e)}")

    def on_moved(self, event):
        """파일 이름 변경 이벤트를 삭제 및 수정 이벤트로 처리"""
        try:
            # 1. 이전 파일에 대한 삭제 이벤트 처리
            delete_event = FileSystemEvent(event.src_path)
            delete_event.event_type = "deleted"
            delete_event = WatcherEvent.from_watchdog_event(delete_event, base_path=self.base_path)
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, delete_event
            )
            
            # 2. 새 파일에 대한 수정 이벤트 처리
            if os.path.getsize(event.dest_path) > MAX_FILE_SIZE:
                logger.warning(f"파일 크기 초과 - 경로: {event.dest_path}, 크기: {os.path.getsize(event.dest_path)}B")
                return
                
            # dest_path를 source_path로 사용하여 새로운 이벤트 생성
            modify_event = FileSystemEvent(event.dest_path)
            modify_event.event_type = "modified"
            modify_event = WatcherEvent.from_watchdog_event(modify_event, base_path=self.base_path)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, modify_event
            )
        except OSError:
            return
        except Exception as e:
            logger.error(f"on_moved 처리 중 오류 발생: {str(e)}")