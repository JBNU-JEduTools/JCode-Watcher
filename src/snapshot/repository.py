"""파일 스냅샷 저장소 구현"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from ..utils.logger import get_logger
from ..utils.exceptions import StorageError

class SnapshotRepository:
    """파일 스냅샷 저장소
    
    파일의 변경 이력을 타임스탬프 기반 스냅샷으로 저장하고 관리합니다.
    각 스냅샷은 원본 파일의 복사본으로, 변경 시점의 상태를 보존합니다.
    """
    
    def __init__(self, base_path: Path):
        """
        Args:
            base_path: 스냅샷 저장 기본 경로
            
        Raises:
            StorageError: 저장소 초기화 실패 시
        """
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
            
        Raises:
            StorageError: 디렉토리 생성 실패 시
        """
        try:
            class_div, hw_dir, student_id, flattened_filename, _ = snapshot_info
            
            # snapshots/os-3/hw1/202012180/folder1@test.c/ 형식으로 경로 생성
            snapshot_dir = self.base_path / class_div / hw_dir / student_id / flattened_filename
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.debug(f"스냅샷 디렉토리 생성: {snapshot_dir}")
            return snapshot_dir
        except Exception as e:
            raise StorageError(f"스냅샷 디렉토리 생성 실패: {e}") from e
        
    def save(self, source_path: Path, snapshot_info: tuple[str, str, str, str, str]) -> Path:
        """새 스냅샷 저장
        
        Args:
            source_path: 원본 파일 경로
            snapshot_info: (class_div, hw_dir, student_id, flattened_filename, original_path)
            
        Returns:
            Path: 저장된 스냅샷 파일 경로
            
        Raises:
            StorageError: 스냅샷 저장 실패 시
        """
        try:
            snapshot_dir = self._get_snapshot_dir(snapshot_info)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_path = snapshot_dir / f"{timestamp}{source_path.suffix}"
            
            shutil.copy2(source_path, snapshot_path)
            self.logger.info(f"새 스냅샷 저장 완료: {snapshot_path}")
            return snapshot_path
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"스냅샷 저장 실패: {e}") from e
            
    def get_latest(self, snapshot_info: tuple[str, str, str, str, str]) -> Optional[Path]:
        """최신 스냅샷 조회
        
        Args:
            snapshot_info: 스냅샷 정보
            
        Returns:
            Optional[Path]: 최신 스냅샷 파일 경로. 스냅샷이 없는 경우 None
            
        Raises:
            StorageError: 스냅샷 조회 실패 시
        """
        try:
            snapshot_dir = self._get_snapshot_dir(snapshot_info)
            snapshots = list(snapshot_dir.glob("*"))
            
            if not snapshots:
                self.logger.debug(f"스냅샷이 없음: {snapshot_dir}")
                return None
                
            latest = max(snapshots, key=lambda x: x.stat().st_mtime)
            self.logger.debug(f"최신 스냅샷 조회: {latest}")
            return latest
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"최신 스냅샷 조회 실패: {e}") from e 