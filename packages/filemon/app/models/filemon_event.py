from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from watchdog.events import FileSystemEvent
from app.models.source_file_info import SourceFileInfo

@dataclass
class FilemonEvent:
    """파일 시스템 이벤트 정보를 담는 클래스"""
    # 이벤트 기본 정보
    event_type: str
    target_file_path: str
    dest_path: str | None  # moved 이벤트의 경우에만 사용
    timestamp: datetime
    
    # 경로 정보
    source_file_info: SourceFileInfo
    
    @classmethod
    def from_components(cls, event: FileSystemEvent, source_file_info: SourceFileInfo) -> 'FilemonEvent':
        """watchdog 이벤트와 파싱된 source_file_info로 Event 생성"""
        target_file_path = event.src_path
        
        # moved 이벤트가 아닌 경우 dest_path를 None으로 설정
        dest_path = getattr(event, 'dest_path', None) if event.event_type == 'moved' else None
        
        return cls(
            event_type=event.event_type,
            target_file_path=target_file_path,
            dest_path=dest_path,
            timestamp=datetime.now(),
            source_file_info=source_file_info
        )