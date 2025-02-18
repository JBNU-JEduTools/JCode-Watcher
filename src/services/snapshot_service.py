"""스냅샷 관리 서비스 구현"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from ..models.metadata import SnapshotMetadata
from ..services.metadata_service import MetadataService
from ..storage.protocols import SnapshotStorage
from ..utils.file_comparator import FileComparator
from ..utils.path_parser import PathParser
from ..utils.logger import get_logger
from ..exceptions import StorageError, MetadataError

class SnapshotManager:
    """스냅샷 관리 클래스"""
    
    def __init__(self, storage: SnapshotStorage, comparator: FileComparator, metadata_service: MetadataService):
        self.storage = storage
        self.comparator = comparator
        self.path_parser = PathParser()
        self.metadata_service = metadata_service
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug("스냅샷 관리자 초기화됨")
        
    def _create_metadata(self, source_path: Path, snapshot_path: Path, snapshot_info: tuple) -> SnapshotMetadata:
        """메타데이터 생성
        
        Args:
            source_path: 원본 파일 경로
            snapshot_path: 스냅샷 파일 경로
            snapshot_info: 스냅샷 정보 튜플
            
        Returns:
            SnapshotMetadata: 생성된 메타데이터
            
        Raises:
            ValueError: 메타데이터 생성에 필요한 정보가 유효하지 않은 경우
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
            raise ValueError(f"메타데이터 생성 실패: {e}") from e
        
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
            
    async def save_snapshot(self, file_path: str) -> None:
        """파일 스냅샷 저장 및 메타데이터 등록
        
        Args:
            file_path: 원본 파일 경로
            
        Raises:
            StorageError: 스냅샷 저장 중 오류 발생 시
            MetadataError: 메타데이터 등록 중 오류 발생 시
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
            
        # 메타데이터 생성 및 등록
        metadata = self._create_metadata(source_path, snapshot_path, snapshot_info)
        await self.metadata_service.register_snapshot(metadata) 