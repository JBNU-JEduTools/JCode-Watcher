from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from watchdog.events import FileSystemEvent
from app.models.source_file_info import SourceFileInfo
from app.config.settings import settings

@dataclass
class Event:
    """파일 시스템 이벤트 정보를 담는 클래스"""
    # 이벤트 기본 정보
    event_type: str
    source_path: str
    dest_path: str | None  # moved 이벤트의 경우에만 사용
    timestamp: datetime
    
    # 경로 정보
    source_file_info: SourceFileInfo
    
    @classmethod
    def from_watchdog_event(cls, event: FileSystemEvent) -> 'Event':
        """watchdog 이벤트로부터 Event 생성"""
        source_path = event.src_path
        # TODO: SourceFileInfo.from_source_path() 메서드 구현 필요
        source_file_info = SourceFileInfo(
            class_div="temp",
            hw_name="temp",
            student_id="temp", 
            filename="temp",
            source_path=Path(source_path)
        )
        
        # moved 이벤트가 아닌 경우 dest_path를 None으로 설정
        dest_path = getattr(event, 'dest_path', '') if event.event_type == 'moved' else None
        
        return cls(
            event_type=event.event_type,
            source_path=source_path,
            dest_path=dest_path,
            timestamp=datetime.now(),
            source_file_info=source_file_info
        )