import shutil
import asyncio
from pathlib import Path
from datetime import datetime
import aiofiles
from typing import Optional
from src.utils.logger import get_logger
from .path_info import PathInfo

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

class SnapshotManager:
    # 파일 비교를 위한 청크 크기
    _CHUNK_SIZE = 8192  # 8KB
    
    def __init__(self, snapshot_dir: str):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def has_changed(self, file_path: str) -> bool:
        """파일 변경 여부 확인"""
        try:
            source = Path(file_path)
            if not source.exists():
                logger.debug(f"파일이 존재하지 않음: {file_path}")
                return False
            
            latest_snapshot = self._get_latest_snapshot(source)
            if not latest_snapshot:
                logger.debug(f"이전 스냅샷이 없음: {file_path}")
                return True
            
            # 1. 먼저 파일 크기 비교 (빠른 체크)
            source_size = source.stat().st_size
            snapshot_size = latest_snapshot.stat().st_size
            
            if source_size != snapshot_size:
                logger.debug(
                    f"파일 크기가 다름 - 원본: {source_size}bytes, "
                    f"스냅샷: {snapshot_size}bytes ({file_path})"
                )
                return True
            
            # 2. 파일 크기가 같다면 내용 비교
            logger.debug(f"파일 내용 비교 시작: {file_path}")
            async with aiofiles.open(source, 'rb') as f1, \
                      aiofiles.open(latest_snapshot, 'rb') as f2:
                chunk_count = 0
                while True:
                    chunk1 = await f1.read(self._CHUNK_SIZE)
                    chunk2 = await f2.read(self._CHUNK_SIZE)
                    chunk_count += 1
                    
                    if chunk1 != chunk2:
                        logger.debug(
                            f"파일 내용이 다름 - 청크 #{chunk_count} "
                            f"({self._CHUNK_SIZE}bytes 단위): {file_path}"
                        )
                        return True
                    if not chunk1:  # EOF
                        break
                    
            logger.debug(f"파일이 동일함 (총 {chunk_count}개 청크 비교): {file_path}")
            return False
            
        except OSError as e:
            logger.error(f"파일 비교 중 오류 발생: {e} ({file_path})")
            return False
    
    async def create_snapshot(self, source_path: str) -> str:
        """스냅샷 생성"""
        path_info = PathInfo.from_source_path(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 최종 스냅샷 경로 생성
        snapshot_path = path_info.get_snapshot_path(self.snapshot_dir, timestamp)
        
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copy2, path_info.source_path, snapshot_path)
            logger.info(f"스냅샷 생성 완료: {snapshot_path}")
            return str(snapshot_path)
        except OSError as e:
            logger.error(f"스냅샷 생성 실패: {e}")
            raise
            
    async def create_empty_snapshot(self, source_path: str) -> Optional[str]:
        """0바이트 스냅샷 생성"""
        path_info = PathInfo.from_source_path(source_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 최종 스냅샷 경로 생성
        snapshot_path = path_info.get_snapshot_path(self.snapshot_dir, timestamp)
        
        try:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            # 0바이트 파일 생성
            snapshot_path.touch()
            logger.info(f"0바이트 스냅샷 생성 완료: {snapshot_path}")
            return str(snapshot_path)
        except OSError as e:
            logger.error(f"0바이트 스냅샷 생성 실패: {e}")
            return None

    def _get_snapshot_dir(self, source: Path) -> Path:
        """스냅샷 디렉토리 경로 생성"""
        relative_path = source.relative_to('/watcher/codes')
        path_parts = relative_path.parts
        
        # 과목-분반과 학번 분리 (os-1-202012180 형식)
        try:
            class_name = '-'.join(path_parts[0].split('-')[:2])  # os-1
            student_id = path_parts[0].split('-')[2]  # 202012180
        except IndexError as e:
            raise ValueError(f"잘못된 경로 형식: {relative_path}") from e
        
        return self.snapshot_dir / class_name / path_parts[1] / student_id / '@'.join(path_parts[2:])

    def _get_latest_snapshot(self, source: Path) -> Optional[Path]:
        """가장 최근 스냅샷 경로 반환"""
        try:
            path_info = PathInfo.from_source_path(source)
            snapshot_dir = path_info.get_snapshot_dir(self.snapshot_dir)
            
            logger.debug(f"스냅샷 디렉토리 검색: {snapshot_dir}")
            
            if not snapshot_dir.exists():
                logger.debug(f"스냅샷 디렉토리가 존재하지 않음: {snapshot_dir}")
                return None
            
            # source.suffix는 이미 점(.)을 포함하고 있으므로 그대로 사용
            snapshots = list(snapshot_dir.glob(f"*{source.suffix}"))
            
            if not snapshots:
                logger.debug(f"스냅샷 파일을 찾을 수 없음 (패턴: *{source.suffix}): {snapshot_dir}")
                return None
            
            latest = max(snapshots, key=lambda p: p.stat().st_mtime)
            logger.debug(f"최신 스냅샷 찾음: {latest} (수정시간: {datetime.fromtimestamp(latest.stat().st_mtime)})")
            return latest
            
        except Exception as e:
            logger.error(f"최신 스냅샷 검색 중 오류 발생: {e}")
            return None