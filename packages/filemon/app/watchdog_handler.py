import asyncio
import os
import re
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import settings
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo
from app.source_path_parser import SourcePathParser

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

class WatchdogHandler(FileSystemEventHandler):
    # 허용되는 파일 패턴 (최대 3depth까지)
    SOURCE_PATTERN_TEMPLATE = r"{base_path}/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/(?:[^/]+/?){{1,4}}[^/]+\.(c|h|py|cpp|hpp)$"
    
    # 무시할 파일 패턴 (정규식)
    IGNORE_PATTERNS = [
        r".*/(?:\.?env|ENV)/.+",          # env, .env, ENV, .ENV
        r".*/(?:site|dist)-packages/.+",   # site-packages, dist-packages
        r".*/lib(?:64|s)?/.+",            # lib, lib64, libs
        r".*/\..+",                        # 숨김 파일/디렉토리
    ]
    
    def __init__(self, event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, parser: SourcePathParser):
        super().__init__()
        self.event_queue = event_queue
        self.loop = loop
        self.base_path = str(settings.WATCH_ROOT)
        self.source_pattern = self.SOURCE_PATTERN_TEMPLATE.format(base_path=self.base_path)
        self.parser = parser

    def _should_process_file(self, file_path: str) -> bool:
        """파일이 처리 대상인지 확인"""
        # 디렉토리는 무시
        if os.path.isdir(file_path):
            return False
        return self._should_process_path(file_path)
    
    def _should_process_path(self, file_path: str) -> bool:
        """파일 경로가 처리 대상인지 확인 (파일 존재 여부와 무관)"""
        # IGNORE_PATTERNS 먼저 체크 (더 빠른 필터링)
        for ignore_pattern in self.IGNORE_PATTERNS:
            if re.search(ignore_pattern, file_path):
                return False
        
        # source_pattern 체크
        return re.search(self.source_pattern, file_path) is not None

    def on_modified(self, event):
        try:
            # 처리 대상 파일인지 확인
            if not self._should_process_file(event.src_path):
                return
                
            if os.path.getsize(event.src_path) > settings.MAX_SAVEABLE_FILE_SIZE:
                logger.warning(f"파일 크기 초과 - 경로: {event.src_path}, 크기: {os.path.getsize(event.src_path)}B")
                return
            
            # 파일 경로 파싱
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            watcher_event = FilemonEvent.from_components(event, source_info)
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
        except OSError:
            return
        except Exception as e:
            logger.error(f"on_modified 처리 중 오류 발생: {str(e)}")

    def on_deleted(self, event):
        try:
            # 처리 대상 파일인지 확인 (삭제는 파일 존재하지 않으므로 경로만으로 확인)
            if not self._should_process_path(event.src_path):
                return
                
            # 파일 경로 파싱
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            watcher_event = FilemonEvent.from_components(event, source_info)
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
            # 삭제 이벤트용 파일 경로 파싱
            parsed_data = self.parser.parse(Path(delete_event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(delete_event.src_path))
            delete_event = FilemonEvent.from_components(delete_event, source_info)
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, delete_event
            )
            
            # 2. 새 파일에 대한 수정 이벤트 처리
            # dest_path 유효성 검증
            if not hasattr(event, 'dest_path') or not event.dest_path or not os.path.exists(event.dest_path):
                logger.warning(f"이동된 파일 경로가 유효하지 않음: {getattr(event, 'dest_path', '경로 없음')}")
                return
            
            # 이동된 파일이 처리 대상인지 확인
            if not self._should_process_file(event.dest_path):
                logger.warning(f"이동된 파일이 처리 대상이 아님: {event.dest_path}")
                return
                
            if os.path.getsize(event.dest_path) > settings.MAX_SAVEABLE_FILE_SIZE:
                logger.warning(f"파일 크기 초과 - 경로: {event.dest_path}, 크기: {os.path.getsize(event.dest_path)}B")
                return
                
            # dest_path를 source_path로 사용하여 새로운 이벤트 생성
            modify_event = FileSystemEvent(event.dest_path)
            modify_event.event_type = "modified"
            # 수정 이벤트용 파일 경로 파싱
            parsed_data = self.parser.parse(Path(modify_event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(modify_event.src_path))
            modify_event = FilemonEvent.from_components(modify_event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, modify_event
            )
        except OSError:
            return
        except Exception as e:
            logger.error(f"on_moved 처리 중 오류 발생: {str(e)}")