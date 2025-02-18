"""스토리지 관련 프로토콜 정의"""
from pathlib import Path
from typing import Optional, Protocol

class SnapshotStorage(Protocol):
    """스냅샷 저장소 프로토콜"""
    
    def save(self, source_path: Path, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """스냅샷 저장"""
        ...
    
    def get_latest(self, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """최신 스냅샷 조회"""
        ... 