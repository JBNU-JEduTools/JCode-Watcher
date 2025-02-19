"""스냅샷 생성

파일 변경 사항을 스냅샷으로 저장합니다.
"""
import asyncio
import shutil
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional

from .utils.logger import get_logger

class SnapshotInfo(NamedTuple):
    """스냅샷 정보"""
    class_div: str      # 과목-분반 (예: "os-3")
    hw_dir: str         # 과제 디렉토리 (예: "hw1")
    student_id: str     # 학번 (예: "202012180")
    filename: str       # 파일명
    original_path: str  # 원본 파일 경로

class SnapshotStorage:
    """스냅샷 저장소"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.logger = get_logger(self.__class__.__name__)
            
    async def create(self, file_path: str, snapshot_info: tuple) -> Optional[Path]:
        """스냅샷 생성
        
        Args:
            file_path: 원본 파일 경로
            snapshot_info: 스냅샷 정보 튜플
            
        Returns:
            Optional[Path]: 생성된 스냅샷 경로 또는 None (변경사항 없는 경우)
            
        Raises:
            OSError: 파일 시스템 작업 실패 시
        """
        info = SnapshotInfo(*snapshot_info)
        source_path = Path(file_path)
        
        if not await self._has_file_changed(source_path, info):
            return None
            
        return await self._create(source_path, info)
            
    async def _has_file_changed(self, source_path: Path, info: SnapshotInfo) -> bool:
        """파일 변경 여부 확인
        
        Args:
            source_path: 검사할 원본 파일 경로
            info: 스냅샷 정보
            
        Returns:
            bool: 파일이 변경되었으면 True, 아니면 False
        """
        snapshot_dir = self._get_snapshot_dir(info)
        if not snapshot_dir.exists():
            return True
            
        files = await asyncio.to_thread(list, snapshot_dir.glob("*"))
        if not files:
            return True
            
        latest = max(files, key=lambda x: x.stat().st_mtime)
        
        # 파일 크기 비교
        if source_path.stat().st_size != latest.stat().st_size:
            return True
            
        # 파일 내용 비교
        chunk_size = 8192
        async with aiofiles.open(source_path, 'rb') as f1, aiofiles.open(latest, 'rb') as f2:
            while True:
                chunk1 = await f1.read(chunk_size)
                chunk2 = await f2.read(chunk_size)
                if chunk1 != chunk2:
                    return True
                if not chunk1:  # EOF
                    return False
            
    def _get_snapshot_dir(self, info: SnapshotInfo) -> Path:
        """스냅샷 디렉토리 경로 생성"""
        return self.base_path / info.class_div / info.hw_dir / info.student_id / info.filename
        
    async def _create(self, source_path: Path, info: SnapshotInfo) -> Path:
        """스냅샷 생성"""
        snapshot_dir = self._get_snapshot_dir(info)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = snapshot_dir / f"{timestamp}{source_path.suffix}"
        
        await asyncio.to_thread(shutil.copy2, source_path, snapshot_path)
        return snapshot_path 