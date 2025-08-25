import shutil
import asyncio
from pathlib import Path
from datetime import datetime
import aiofiles
from typing import Optional

# from old.utils.logger import get_logger # TODO: logger
from app.models.source_file_info import SourceFileInfo
from app.parser import SourceFileParser
from app.config.settings import settings

# # 모듈 레벨 로거 설정
# logger = get_logger(__name__)

class SnapshotManager:
    # 파일 비교를 위한 청크 크기
    _CHUNK_SIZE = 8192  # 8KB
    
    def __init__(self):
        self.parser = SourceFileParser()
        settings.SNAPSHOT_BASE.mkdir(parents=True, exist_ok=True)
        # logger.info(f"스냅샷 관리자 초기화 - 경로: {self.parser.SNAPSHOT_BASE}")
    
    async def has_changed(self, file_path: str) -> bool:
        """파일 변경 여부 확인"""
        try:
            source = Path(file_path)
            if not source.exists():
                # logger.debug(f"파일 없음 - 경로: {file_path}")
                return False
            
            path_info = self.parser.parse(file_path)
            latest_snapshot = self._get_latest_snapshot(path_info)
            
            if not latest_snapshot:
                # logger.debug(
                #     f"이전 스냅샷 없음 - 원본: {file_path}, "
                #     f"스냅샷 경로: {path_info.filename}"
                # )
                return True
            
            # 1. 먼저 파일 크기 비교 (빠른 체크)
            source_size = source.stat().st_size
            snapshot_size = latest_snapshot.stat().st_size
            
            if source_size != snapshot_size:
                # logger.debug(
                #     f"크기 불일치 - 원본: {source_size}B, "
                #     f"스냅샷: {snapshot_size}B, "
                #     f"경로: {path_info.filename}"
                # )
                return True
            
            # 2. 파일 크기가 같다면 내용 비교
            # logger.debug(f"내용 비교 시작 - 경로: {path_info.filename}")
            async with aiofiles.open(source, 'rb') as f1, \
                      aiofiles.open(latest_snapshot, 'rb') as f2:
                chunk_count = 0
                while True:
                    chunk1 = await f1.read(self._CHUNK_SIZE)
                    chunk2 = await f2.read(self._CHUNK_SIZE)
                    chunk_count += 1
                    
                    if chunk1 != chunk2:
                        # logger.debug(
                        #     f"내용 불일치 - 청크: {chunk_count}, "
                        #     f"크기: {self._CHUNK_SIZE}B, 경로: {path_info.filename}"
                        # )
                        return True
                    if not chunk1:  # EOF
                        break
                    
            # logger.debug(f"파일 동일 - 청크수: {chunk_count}, 경로: {path_info.filename}")
            return False
            
        except OSError as e:
            # logger.error(f"비교 실패 - 경로: {file_path}, 오류: {str(e)}")
            return False
    
    async def create_snapshot(self, source_path: str) -> str:
        """스냅샷 생성"""
        path_info = self.parser.parse(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        snapshot_path = self.parser.get_snapshot_path(path_info, timestamp)
        
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, source_path, snapshot_path)
            # logger.info(f"스냅샷 생성 완료 - 경로: {snapshot_path}")
            return str(snapshot_path)
        except OSError as e:
            # logger.error(f"스냅샷 생성 실패 - 오류: {str(e)}")
            raise
            
    async def create_empty_snapshot(self, source_path: str) -> Optional[str]:
        """빈 스냅샷 생성"""
        path_info = self.parser.parse(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        snapshot_path = self.parser.get_snapshot_path(path_info, timestamp)
        
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.touch()
            # logger.info(f"빈 스냅샷 생성 완료 - 경로: {snapshot_path}")
            return str(snapshot_path)
        except OSError as e:
            # logger.error(f"빈 스냅샷 생성 실패 - 오류: {str(e)}")
            return None

    def _get_latest_snapshot(self, path_info: SourceFileInfo) -> Optional[Path]:
        """가장 최근 스냅샷 경로 반환"""
        try:
            snapshot_dir = self.parser.get_snapshot_dir(path_info)
            
            # logger.debug(f"스냅샷 디렉토리 검색 - 경로: {snapshot_dir}")
            
            if not snapshot_dir.exists():
                # logger.debug(f"스냅샷 디렉토리 없음 - 경로: {snapshot_dir}")
                return None
            
            snapshots = list(snapshot_dir.glob(f"*{path_info.source_path.suffix}"))
            
            if not snapshots:
                # logger.debug(f"스냅샷 없음 - 패턴: *{path_info.source_path.suffix}, 경로: {snapshot_dir}")
                return None
            
            latest = max(snapshots, key=lambda p: p.stat().st_mtime)
            # logger.debug(
            #     f"최신 스냅샷 발견 - 경로: {latest}, "
            #     f"수정시각: {datetime.fromtimestamp(latest.stat().st_mtime)}"
            # )
            return latest
            
        except Exception as e:
            # logger.error(f"최신 스냅샷 검색 실패 - 오류: {str(e)}")
            return None
