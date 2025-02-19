"""소스코드 이벤트 처리

소스코드 파일의 변경 이벤트를 감지하고 처리합니다.
"""
from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .source_code_path import SourceCodePath, SourceCodeInfo
from .utils.event_queue import EventQueue
from .utils.logger import get_logger
from .utils.exceptions import InvalidSourcePathError

logger = get_logger(__name__)

class SourceCodeEventHandler(FileSystemEventHandler):
    """소스코드 이벤트 처리기
    
    파일 시스템에서 발생하는 소스코드 변경 이벤트를 감지하고 필터링합니다.
    """
    
    def __init__(self, path_manager: SourceCodePath, event_queue: EventQueue):
        """
        Args:
            path_manager: 경로 관리자
            event_queue: 이벤트 큐
        """
        self.path_manager = path_manager
        self.event_queue = event_queue
        self.logger = get_logger(self.__class__.__name__)
        
    def on_modified(self, event: FileModifiedEvent) -> None:
        """파일 수정 이벤트 처리
        
        Args:
            event: 파일 수정 이벤트
        """
        if not isinstance(event, FileModifiedEvent):
            return
            
        file_path = event.src_path
        
        # 디렉토리 이벤트는 무시
        if event.is_directory:
            logger.debug(f"이벤트 필터링: 디렉토리 이벤트 무시 ({file_path})")
            return
            
        # 제외 대상 파일인지 확인
        if self.path_manager.is_excluded(file_path):
            return
            
        try:
            # 경로 정보 파싱 및 검증
            source_info = self.path_manager.parse_path(file_path)
            
            # 이벤트 큐에 추가
            self.event_queue.put_event_threadsafe("modified", source_info)
            logger.debug(f"이벤트 감지: 큐에 추가됨 ({file_path})")
            
        except InvalidSourcePathError as e:
            logger.warning(f"이벤트 필터링: 잘못된 소스코드 경로 형식 ({str(e)})")
            
        except Exception as e:
            logger.error(f"소스코드 변경 이벤트 처리 실패: {str(e)}", exc_info=True)
            raise 