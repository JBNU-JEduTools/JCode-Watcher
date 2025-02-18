"""스냅샷 저장소 프로토콜 정의"""
from pathlib import Path
from typing import Optional, Protocol

class SnapshotStorage(Protocol):
    """스냅샷 저장소 인터페이스
    
    파일 스냅샷의 저장과 조회를 위한 기본 인터페이스를 정의합니다.
    이 프로토콜을 구현하는 클래스는 파일 시스템, 데이터베이스 등
    다양한 백엔드 저장소를 지원할 수 있습니다.
    """
    
    def save(self, source_path: Path, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """새 스냅샷 저장
        
        Args:
            source_path: 원본 파일 경로
            snapshot_info: (class_div, hw_dir, student_id, flattened_filename, original_path)
            
        Returns:
            Optional[Path]: 저장된 스냅샷 파일 경로. 실패 시 None
        """
        ...
    
    def get_latest(self, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """최신 스냅샷 조회
        
        Args:
            snapshot_info: 스냅샷 정보
            
        Returns:
            Optional[Path]: 최신 스냅샷 파일 경로. 스냅샷이 없는 경우 None
        """
        ... 