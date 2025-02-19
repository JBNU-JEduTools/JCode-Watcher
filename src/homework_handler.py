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
            logger.debug(f"Directory event ignored: {file_path}")
            return
            
        # 무시해야 할 파일인지 확인
        if self.path_manager.should_ignore(file_path):
            return
            
        try:
            # 경로 정보 파싱 및 검증
            homework_info = self.path_manager.parse_path(file_path)
            
            # 이벤트 큐에 추가
            self.event_queue.put_event_threadsafe("modified", homework_info)
            logger.debug(f"Added event for: {file_path}")
            
        except InvalidHomeworkPathError as e:
            # 잘못된 과제 경로는 warning으로 로깅하고 무시
            logger.warning(f"Invalid homework path: {file_path} - {str(e)}")
            
        except Exception as e:
            # 예상치 못한 에러는 error로 로깅하고 전파
            logger.error(f"Unexpected error while handling file: {file_path}", exc_info=True)
            raise 