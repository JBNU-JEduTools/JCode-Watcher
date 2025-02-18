"""파일 시스템 이벤트 핸들러 구현"""
import logging
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from ..utils.event_queue import EventQueue
from ..utils.file_filter import FileFilter

class FileChangeHandler(FileSystemEventHandler):
    """파일 시스템 이벤트 핸들러"""
    
    def __init__(self, event_queue: EventQueue, file_filter: FileFilter):
        self.event_queue = event_queue
        self.file_filter = file_filter
        logging.info("FileChangeHandler 초기화됨")
        logging.info(f"허용된 파일 확장자: {file_filter.allowed_extensions}")
        logging.info(f"무시할 패턴: {file_filter.ignore_patterns}")
        
    def on_modified(self, event: FileModifiedEvent):
        """파일 수정 이벤트 처리 (외부 스레드에서 호출)"""
        logging.info(f"이벤트 감지됨: type={event.__class__.__name__}, path={event.src_path}")
        
        if event.is_directory:
            logging.info(f"디렉토리 이벤트 무시: {event.src_path}")
            return
            
        file_path = str(event.src_path)
        logging.debug(f"파일 경로 처리: {file_path}")
        
        if self.file_filter.should_ignore(file_path):
            logging.info(f"필터에 의해 무시됨: {file_path}")
            return
            
        # 스레드 안전한 방식으로 이벤트 추가
        try:
            self.event_queue.put_event_threadsafe("modified", file_path)
            logging.info(f"이벤트 큐에 추가됨: {file_path}")
        except Exception as e:
            logging.error(f"이벤트 큐 추가 실패: {e}") 