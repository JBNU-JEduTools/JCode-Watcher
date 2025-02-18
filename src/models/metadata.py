"""메타데이터 모델 정의"""
from typing import TypedDict

class SnapshotMetadata(TypedDict):
    """스냅샷 메타데이터 타입"""
    class_div: str
    homework_dir: str
    student_id: str
    filename: str
    original_path: str
    snapshot_path: str
    timestamp: str
    file_size: int 