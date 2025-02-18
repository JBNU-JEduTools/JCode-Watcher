"""스냅샷 관리 모듈

파일 변경 사항을 스냅샷으로 저장하고, 관련 메타데이터를 API 서버에 등록합니다.
스냅샷은 타임스탬프 기반으로 저장되며, 파일 내용이 실제로 변경된 경우에만 새로운 스냅샷을 생성합니다.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from ..api.schemas import SnapshotRequest
from ..api.client import SnapshotApiClient
from .protocols import SnapshotStorage
from ..utils.file_comparator import FileComparator
from ..utils.path_parser import PathParser
from ..utils.logger import get_logger
from ..utils.exceptions import StorageError, MetadataError

class SnapshotManager:
    """스냅샷 관리 클래스
    
    파일 변경 사항을 스냅샷으로 저장하고 API 서버에 등록하는 역할을 담당합니다.
    파일 내용이 실제로 변경된 경우에만 새로운 스냅샷을 생성하여 중복을 방지합니다.
    """
    
    def __init__(self, storage: SnapshotStorage, comparator: FileComparator, api_client: SnapshotApiClient):
        """
        Args:
            storage: 스냅샷 저장소
            comparator: 파일 비교기
            api_client: API 클라이언트
        """
        self.storage = storage
        self.comparator = comparator
        self.path_parser = PathParser()
        self.api_client = api_client
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug("스냅샷 관리자 초기화됨")
        
    def _create_request(self, source_path: Path, snapshot_path: Path, snapshot_info: tuple) -> SnapshotRequest:
        """API 요청 데이터 생성
        
        Args:
            source_path: 원본 파일 경로
            snapshot_path: 스냅샷 파일 경로
            snapshot_info: (class_div, hw_dir, student_id, filename, original_path)
            
        Returns:
            SnapshotRequest: API 요청 데이터
            
        Raises:
            ValueError: 요청 데이터 생성에 필요한 정보가 유효하지 않은 경우
        """
        try:
            class_div, hw_dir, student_id, filename, original_path = snapshot_info
            return {
                "class_div": class_div,
                "homework_dir": hw_dir,
                "student_id": student_id,
                "filename": filename,
                "original_path": original_path,
                "snapshot_path": str(snapshot_path),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "file_size": source_path.stat().st_size
            }
        except Exception as e:
            raise ValueError(f"API 요청 데이터 생성 실패: {e}") from e
        
    async def _save_snapshot(self, source_path: Path, snapshot_info: tuple) -> Optional[Path]:
        """스냅샷 저장 처리
        
        Args:
            source_path: 원본 파일 경로
            snapshot_info: 스냅샷 정보 튜플
            
        Returns:
            Optional[Path]: 저장된 스냅샷 경로. 변경사항이 없는 경우 None
            
        Raises:
            StorageError: 스냅샷 저장 중 오류 발생 시
        """
        latest_snapshot = self.storage.get_latest(snapshot_info)
        if latest_snapshot and not self.comparator.is_different(source_path, latest_snapshot):
            self.logger.info(f"변경사항 없음, 스냅샷 저장 건너뜀: {source_path}")
            return None
            
        return self.storage.save(source_path, snapshot_info)
            
    async def process_file_change(self, file_path: str) -> None:
        """파일 변경 처리
        
        변경된 파일의 스냅샷을 저장하고 API 서버에 등록합니다.
        파일 내용이 실제로 변경된 경우에만 새로운 스냅샷을 생성합니다.
        
        Args:
            file_path: 변경된 파일 경로
            
        Raises:
            StorageError: 스냅샷 저장 중 오류 발생 시
            MetadataError: API 서버 통신 중 오류 발생 시
            ValueError: 파일 경로가 유효하지 않은 경우
        """
        source_path = Path(file_path)
        if not source_path.exists():
            raise ValueError(f"파일이 존재하지 않습니다: {file_path}")
            
        snapshot_info = self.path_parser.parse_path(file_path)
        
        # 스냅샷 저장
        snapshot_path = await self._save_snapshot(source_path, snapshot_info)
        if not snapshot_path:  # 정상적인 "변경 없음" 상황
            return
            
        # API 요청 데이터 생성 및 전송
        request_data = self._create_request(source_path, snapshot_path, snapshot_info)
        await self.api_client.register_snapshot(request_data) 