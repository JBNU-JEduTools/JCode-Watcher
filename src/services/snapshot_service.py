"""스냅샷 관리 서비스 구현"""
from datetime import datetime
from pathlib import Path
from ..models.metadata import SnapshotMetadata
from ..services.metadata_service import MetadataService
from ..storage.protocols import SnapshotStorage
from ..utils.file_comparator import FileComparator
from ..utils.path_parser import PathParser
from ..utils.logger import get_logger

class SnapshotManager:
    """스냅샷 관리 클래스"""
    
    def __init__(self, storage: SnapshotStorage, comparator: FileComparator, metadata_service: MetadataService):
        self.storage = storage
        self.comparator = comparator
        self.path_parser = PathParser()
        self.metadata_service = metadata_service
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug("스냅샷 관리자 초기화됨")
        
    async def save_snapshot(self, file_path: str) -> None:
        """파일 스냅샷 저장"""
        try:
            source_path = Path(file_path)
            snapshot_info = self.path_parser.parse_path(file_path)
            
            # 최근 스냅샷과 비교
            latest_snapshot = self.storage.get_latest(snapshot_info)
            if latest_snapshot:
                try:
                    if not self.comparator.is_different(source_path, latest_snapshot):
                        self.logger.info(f"변경사항 없음, 스냅샷 저장 건너뜀: {source_path}")
                        return
                except Exception as e:
                    self.logger.warning(f"파일 비교 중 오류 발생, 스냅샷 계속 진행: {e}")
            
            # 스냅샷 저장
            snapshot_path = self.storage.save(source_path, snapshot_info)
            if snapshot_path:
                # 메타데이터 생성
                class_div, hw_dir, student_id, filename, original_path = snapshot_info
                metadata: SnapshotMetadata = {
                    "class_div": class_div,
                    "homework_dir": hw_dir,
                    "student_id": student_id,
                    "filename": filename,
                    "original_path": original_path,
                    "snapshot_path": str(snapshot_path),
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "file_size": source_path.stat().st_size
                }
                
                # 메타데이터 등록 (실패는 하위 컴포넌트에서 처리)
                await self.metadata_service.register_snapshot(metadata)
            
        except Exception as e:
            self.logger.error(f"스냅샷 저장 중 오류 발생: {e}") 