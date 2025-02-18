"""파일 변경 이벤트 처리"""
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from ..utils.event_queue import EventQueue
from ..utils.file_filter import FileFilter
from ..utils.logger import get_logger

class ChangeObserver(FileSystemEventHandler):
    """파일 시스템 변경 이벤트 처리
    
    파일 시스템의 변경 이벤트를 감지하고 필터링하여
    처리가 필요한 이벤트만 이벤트 큐에 추가합니다.
    """
    
    def __init__(self, event_queue: EventQueue, file_filter: FileFilter):
        """
        Args:
            event_queue: 변경 이벤트를 저장할 이벤트 큐
            file_filter: 파일 필터링을 위한 필터 객체
        """
        self.event_queue = event_queue
        self.file_filter = file_filter
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info("변경 감지 옵저버 초기화됨")
        self.logger.debug(f"허용된 파일 확장자: {file_filter.allowed_extensions}")
        self.logger.debug(f"무시할 패턴: {file_filter.ignore_patterns}")
        
    def on_modified(self, event: FileModifiedEvent):
        """파일 수정 이벤트 처리
        
        Args:
            event: 파일 시스템 수정 이벤트
            
        Note:
            이 메서드는 외부 스레드(watchdog)에서 호출되므로,
            스레드 안전한 방식으로 이벤트를 큐에 추가합니다.
        """
        self.logger.debug(f"이벤트 감지됨: type={event.__class__.__name__}, path={event.src_path}")
        
        if event.is_directory:
            self.logger.debug(f"디렉토리 이벤트 무시: {event.src_path}")
            return
            
        file_path = str(event.src_path)
        self.logger.debug(f"파일 경로 처리: {file_path}")
        
        if self.file_filter.should_ignore(file_path):
            self.logger.debug(f"필터에 의해 무시됨: {file_path}")
            return
            
        # 스레드 안전한 방식으로 이벤트 추가
        try:
            self.event_queue.put_event_threadsafe("modified", file_path)
            self.logger.debug(f"이벤트 큐에 추가됨: {file_path}")
        except Exception as e:
            self.logger.error(f"이벤트 큐 추가 실패: {e}") 