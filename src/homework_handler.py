"""과제 파일 이벤트 처리

학생들의 과제 파일 변경 이벤트를 처리합니다.
"""
from pathlib import Path
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .homework_path import HomeworkPath, HomeworkInfo
from .utils.event_queue import EventQueue
from .utils.logger import get_logger
from .utils.exceptions import InvalidHomeworkPathError

logger = get_logger(__name__)

class HomeworkHandler(FileSystemEventHandler):
    """과제 파일 이벤트 처리기
    
    학생들의 과제 파일 변경 이벤트를 처리합니다.
    """
    
    def __init__(self, path_manager: HomeworkPath, event_queue: EventQueue):
        """
        Args:
            path_manager: 과제 경로 관리자
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
            logger.debug(f"디렉토리 변경 이벤트는 처리하지 않습니다: {file_path}")
            return
            
        # 무시해야 할 파일인지 확인
        if self.path_manager.should_ignore(file_path):
            return
            
        try:
            # 경로 정보 파싱 및 검증
            homework_info = self.path_manager.parse_path(file_path)
            
            # 이벤트 큐에 추가
            self.event_queue.put_event_threadsafe("modified", homework_info)
            logger.debug(f"과제 파일 변경을 감지했습니다: {file_path}")
            
        except InvalidHomeworkPathError as e:
            logger.warning(f"과제 파일 경로가 올바르지 않습니다: {str(e)}")
            
        except Exception as e:
            logger.error(f"과제 파일 처리 중 예상치 못한 오류가 발생했습니다: {str(e)}", exc_info=True)
            raise 