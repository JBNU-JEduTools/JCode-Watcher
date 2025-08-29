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
        logger.debug("파일 처리 대상 검사 시작", file_path=file_path)
        
        # 디렉토리는 무시
        if os.path.isdir(file_path):
            logger.debug("디렉토리이므로 처리 제외", file_path=file_path)
            return False
            
        result = self._should_process_path(file_path)
        logger.debug("파일 처리 대상 검사 완료", file_path=file_path, should_process=result)
        return result
    
    def _should_process_path(self, file_path: str) -> bool:
        """파일 경로가 처리 대상인지 확인 (파일 존재 여부와 무관)"""
        logger.debug("경로 처리 대상 검사 시작", file_path=file_path)
        
        # IGNORE_PATTERNS 먼저 체크 (더 빠른 필터링)
        for i, ignore_pattern in enumerate(self.IGNORE_PATTERNS):
            if re.search(ignore_pattern, file_path):
                logger.debug("무시 패턴에 매칭됨", file_path=file_path, 
                           pattern_index=i, pattern=ignore_pattern)
                return False
        
        logger.debug("무시 패턴 검사 통과", file_path=file_path)
        
        # source_pattern 체크
        source_match = re.search(self.source_pattern, file_path)
        if source_match:
            logger.debug("소스 패턴 매칭됨", file_path=file_path, 
                        pattern=self.source_pattern, match_groups=source_match.groups())
            return True
        else:
            logger.debug("소스 패턴 매칭 실패", file_path=file_path, pattern=self.source_pattern)
            return False

    def on_modified(self, event):
        logger.debug("파일 수정 이벤트 수신", event_type="modified", src_path=event.src_path)
        
        try:
            # 처리 대상 파일인지 확인
            if not self._should_process_file(event.src_path):
                logger.debug("파일 처리 대상 아님", src_path=event.src_path)
                return
            
            logger.debug("파일 처리 대상 확인됨", src_path=event.src_path)
                
            file_size = os.path.getsize(event.src_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                logger.warning("파일 크기 초과", src_path=event.src_path, 
                             file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                return
            
            logger.debug("파일 크기 검증 통과", src_path=event.src_path, file_size=file_size)
            
            # 파일 경로 파싱
            logger.debug("파일 경로 파싱 시작", src_path=event.src_path)
            parsed_data = self.parser.parse(Path(event.src_path))
            logger.debug("파일 경로 파싱 완료", src_path=event.src_path,
                        class_div=parsed_data.get('class_div'),
                        hw_name=parsed_data.get('hw_name'),
                        student_id=parsed_data.get('student_id'),
                        filename=parsed_data.get('filename'))
            
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            logger.debug("SourceFileInfo 생성 완료", src_path=event.src_path)
            
            watcher_event = FilemonEvent.from_components(event, source_info)
            logger.debug("FilemonEvent 생성 완료", src_path=event.src_path, event_type="modified")
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
            logger.debug("이벤트 큐에 추가 완료", src_path=event.src_path, event_type="modified")
            
        except OSError as e:
            logger.debug("OSError 발생 - 처리 중단", src_path=event.src_path, error=str(e))
            return
        except Exception as e:
            logger.error("on_modified 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, error=str(e), exc_info=True)

    def on_deleted(self, event):
        logger.debug("파일 삭제 이벤트 수신", event_type="deleted", src_path=event.src_path)
        
        try:
            # 처리 대상 파일인지 확인 (삭제는 파일 존재하지 않으므로 경로만으로 확인)
            if not self._should_process_path(event.src_path):
                logger.debug("삭제된 파일이 처리 대상 아님", src_path=event.src_path)
                return
            
            logger.debug("삭제된 파일이 처리 대상 확인됨", src_path=event.src_path)
                
            # 파일 경로 파싱
            logger.debug("삭제된 파일 경로 파싱 시작", src_path=event.src_path)
            parsed_data = self.parser.parse(Path(event.src_path))
            logger.debug("삭제된 파일 경로 파싱 완료", src_path=event.src_path,
                        class_div=parsed_data.get('class_div'),
                        hw_name=parsed_data.get('hw_name'),
                        student_id=parsed_data.get('student_id'),
                        filename=parsed_data.get('filename'))
            
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            logger.debug("삭제 이벤트용 SourceFileInfo 생성 완료", src_path=event.src_path)
            
            watcher_event = FilemonEvent.from_components(event, source_info)
            logger.debug("삭제 이벤트용 FilemonEvent 생성 완료", src_path=event.src_path, event_type="deleted")
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, watcher_event
            )
            logger.debug("삭제 이벤트 큐에 추가 완료", src_path=event.src_path, event_type="deleted")
            
        except Exception as e:
            logger.error("on_deleted 처리 중 예상치 못한 오류 발생", 
                        src_path=event.src_path, error=str(e), exc_info=True)


    def on_moved(self, event):
        """파일 이름 변경 이벤트를 삭제 및 수정 이벤트로 처리"""
        logger.debug("파일 이동 이벤트 수신", event_type="moved", 
                    src_path=event.src_path, 
                    dest_path=getattr(event, 'dest_path', None))
        
        try:
            # 1. 이전 파일에 대한 삭제 이벤트 처리
            logger.debug("이동 이벤트 - 삭제 처리 시작", src_path=event.src_path)
            delete_event = FileSystemEvent(event.src_path)
            delete_event.event_type = "deleted"
            
            # 삭제 이벤트용 파일 경로 파싱
            logger.debug("이동 이벤트 - 삭제용 경로 파싱 시작", src_path=event.src_path)
            parsed_data = self.parser.parse(Path(delete_event.src_path))
            logger.debug("이동 이벤트 - 삭제용 경로 파싱 완료", src_path=event.src_path,
                        class_div=parsed_data.get('class_div'),
                        hw_name=parsed_data.get('hw_name'),
                        student_id=parsed_data.get('student_id'),
                        filename=parsed_data.get('filename'))
            
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(delete_event.src_path))
            delete_event = FilemonEvent.from_components(delete_event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, delete_event
            )
            logger.debug("이동 이벤트 - 삭제 이벤트 큐에 추가 완료", src_path=event.src_path)
            
            # 2. 새 파일에 대한 수정 이벤트 처리
            # dest_path 유효성 검증
            dest_path = getattr(event, 'dest_path', None)
            if not dest_path:
                logger.warning("이동된 파일의 dest_path 속성이 없음", src_path=event.src_path)
                return
                
            if not os.path.exists(dest_path):
                logger.warning("이동된 파일이 존재하지 않음", src_path=event.src_path, dest_path=dest_path)
                return
            
            logger.debug("이동 이벤트 - 수정 처리 시작", dest_path=dest_path)
            
            # 이동된 파일이 처리 대상인지 확인
            if not self._should_process_file(dest_path):
                logger.debug("이동된 파일이 처리 대상 아님", dest_path=dest_path)
                return
            
            logger.debug("이동된 파일이 처리 대상 확인됨", dest_path=dest_path)
                
            file_size = os.path.getsize(dest_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                logger.warning("이동된 파일 크기 초과", dest_path=dest_path, 
                             file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                return
            
            logger.debug("이동된 파일 크기 검증 통과", dest_path=dest_path, file_size=file_size)
                
            # dest_path를 source_path로 사용하여 새로운 이벤트 생성
            modify_event = FileSystemEvent(dest_path)
            modify_event.event_type = "modified"
            
            # 수정 이벤트용 파일 경로 파싱
            logger.debug("이동 이벤트 - 수정용 경로 파싱 시작", dest_path=dest_path)
            parsed_data = self.parser.parse(Path(modify_event.src_path))
            logger.debug("이동 이벤트 - 수정용 경로 파싱 완료", dest_path=dest_path,
                        class_div=parsed_data.get('class_div'),
                        hw_name=parsed_data.get('hw_name'),
                        student_id=parsed_data.get('student_id'),
                        filename=parsed_data.get('filename'))
            
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(modify_event.src_path))
            modify_event = FilemonEvent.from_components(modify_event, source_info)
            
            self.loop.call_soon_threadsafe(
                self.event_queue.put_nowait, modify_event
            )
            logger.debug("이동 이벤트 - 수정 이벤트 큐에 추가 완료", dest_path=dest_path)
            
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