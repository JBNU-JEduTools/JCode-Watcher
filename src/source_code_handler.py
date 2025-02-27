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
        
        다음 순서로 이벤트를 필터링하고 처리합니다:
        1. FileModifiedEvent 타입 검증
        2. 디렉토리 이벤트 필터링
        3. 제외 대상 파일 필터링
        4. 경로 정보 파싱 및 검증
        5. 이벤트 큐에 추가
        
        Args:
            event: 파일 수정 이벤트
        """
        # 1. 이벤트 타입 검증
        if not isinstance(event, FileModifiedEvent):
            return
            
        file_path = event.src_path
        
        # 2. 디렉토리 이벤트 필터링
        if self._is_directory_event(event):
            return
            
        # 3. 제외 대상 파일 필터링
        if self.path_manager.is_excluded(file_path):
            return
            
        try:
            # 4. 경로 정보 파싱 및 검증
            source_info = self.path_manager.parse_path(file_path)
            
            # 5. 이벤트 큐에 추가
            self._queue_event(source_info)
            
        except InvalidSourcePathError as e:
            logger.warning(f"이벤트 필터링: 잘못된 소스코드 경로 형식 ({str(e)})")
            
        except Exception as e:
            logger.error(f"소스코드 변경 이벤트 처리 실패: {str(e)}", exc_info=True)
            raise
            
    def _is_directory_event(self, event: FileModifiedEvent) -> bool:
        """디렉토리 이벤트인지 확인"""
        if event.is_directory:
            try:
                # 경로 정보 파싱 시도
                info = self.path_manager.parse_path(event.src_path)
                logger.debug(
                    f"이벤트 필터링: 디렉토리 이벤트 무시 "
                    f"[{info.class_div}/{info.student_id}/{info.hw_dir}/{Path(event.src_path).name}]"
                )
            except InvalidSourcePathError:
                # 파싱 실패 시 기본 로그 출력
                logger.debug(f"이벤트 필터링: 디렉토리 이벤트 무시 ({event.src_path})")
            return True
        return False
        
    def _queue_event(self, source_info: SourceCodeInfo) -> None:
        """이벤트를 큐에 추가"""
        self.event_queue.put_event_threadsafe("modified", source_info)
        logger.debug(
            f"이벤트 감지: 큐에 추가됨 "
            f"[{source_info.class_div}/{source_info.student_id}/{source_info.hw_dir}/{Path(source_info.original_path).name}]"
        ) 