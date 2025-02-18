"""과제 파일 이벤트 처리

학생들의 과제 파일 변경 이벤트를 처리합니다.
"""
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .homework_path import HomeworkPath
from .utils.event_queue import EventQueue
from .utils.file_filter import FileFilter
from .utils.logger import get_logger

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
        self.file_filter = FileFilter()
        
    def on_modified(self, event: FileModifiedEvent) -> None:
        """파일 수정 이벤트 처리"""
        if event.is_directory:
            return
            
        file_path = str(event.src_path)
        
        # 파일 필터링
        if not self.path_manager.is_valid_path(file_path):
            return
            
        if self.file_filter.should_ignore(file_path):
            return
            
        # 이벤트 처리
        if self.path_manager.parse_path(file_path):
            self.event_queue.put_event_threadsafe("modified", file_path)
            self.logger.debug(f"과제 파일 변경 감지: {file_path}") 