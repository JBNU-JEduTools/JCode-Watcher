"""API 요청/응답 스키마 정의"""
from typing import TypedDict

class SnapshotRequest(TypedDict):
    """스냅샷 등록 API 요청 스키마
    
    스냅샷 메타데이터를 API 서버에 전송할 때 사용되는
    요청 본문의 구조를 정의합니다.
    """
    class_div: str      # 과목-분반 (예: "os-3")
    homework_dir: str   # 과제 디렉토리명 (예: "hw1")
    student_id: str     # 학번 (예: "202012180")
    filename: str       # 파일명 (예: "test.c")
    original_path: str  # 원본 파일 경로
    snapshot_path: str  # 스냅샷 파일 경로
    timestamp: str      # 스냅샷 생성 시간 (YYYYMMDD_HHMMSS 형식)
    file_size: int      # 파일 크기 (바이트)

class SnapshotMetadata(TypedDict):
    """파일 스냅샷 메타데이터
    
    파일의 각 스냅샷에 대한 메타데이터를 정의합니다.
    API 서버와의 동기화에 사용됩니다.
    """
    class_div: str      # 과목-분반 (예: "os-3")
    homework_dir: str   # 과제 디렉토리명 (예: "hw1")
    student_id: str     # 학번 (예: "202012180")
    filename: str       # 파일명 (예: "test.c")
    original_path: str  # 원본 파일 경로
    snapshot_path: str  # 스냅샷 파일 경로
    timestamp: str      # 스냅샷 생성 시간 (YYYYMMDD_HHMMSS 형식)
    file_size: int      # 파일 크기 (바이트) 