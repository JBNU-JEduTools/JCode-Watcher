"""파일시스템 기반 스냅샷 저장소 구현"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from ..utils.logger import get_logger

class FileSystemSnapshotStorage:
    """파일 시스템 기반 스냅샷 저장소"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug(f"스냅샷 저장소 초기화: {base_path}")
        
    def _get_snapshot_dir(self, snapshot_info: tuple[str, str, str, str, str]) -> Path:
        """스냅샷 디렉토리 경로 생성
        
        Args:
            snapshot_info: (class_div, hw_dir, student_id, flattened_filename, original_path)
            예: ('os-3', 'hw1', '202012180', 'folder1@test.c', '/original/path/test.c')
            
        Returns:
            Path: snapshots/os-3/hw1/202012180/folder1@test.c/ 형식의 경로
        """
        class_div, hw_dir, student_id, flattened_filename, _ = snapshot_info
        
        # snapshots/os-3/hw1/202012180/folder1@test.c/ 형식으로 경로 생성
        snapshot_dir = self.base_path / class_div / hw_dir / student_id / flattened_filename
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"스냅샷 디렉토리 생성: {snapshot_dir}")
        return snapshot_dir
        
    def save(self, source_path: Path, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """스냅샷 저장
        
        Args:
            source_path: 원본 파일 경로
            snapshot_info: (class_div, hw_dir, student_id, flattened_filename, original_path)
            
        Returns:
            Optional[Path]: 저장된 스냅샷 경로 또는 None
        """
        snapshot_dir = self._get_snapshot_dir(snapshot_info)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = snapshot_dir / f"{timestamp}{source_path.suffix}"
        
        try:
            shutil.copy2(source_path, snapshot_path)
            self.logger.info(f"스냅샷 저장 완료: {snapshot_path}")
            return snapshot_path
        except Exception as e:
            self.logger.error(f"스냅샷 저장 실패: {e}")
            return None
            
    def get_latest(self, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """최신 스냅샷 조회"""
        snapshot_dir = self._get_snapshot_dir(snapshot_info)
        try:
            snapshots = list(snapshot_dir.glob("*"))
            if not snapshots:
                self.logger.debug(f"스냅샷이 없음: {snapshot_dir}")
                return None
            latest = max(snapshots, key=lambda x: x.stat().st_mtime)
            self.logger.debug(f"최신 스냅샷 조회: {latest}")
            return latest
        except Exception as e:
            self.logger.error(f"최신 스냅샷 조회 실패: {e}")
            return None 