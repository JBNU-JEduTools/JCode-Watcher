import aiofiles
from pathlib import Path
from datetime import datetime
from app.models.source_file_info import SourceFileInfo
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SnapshotManager:
    """스냅샷 관리자"""
    
    def __init__(self):
        pass

    async def create_snapshot_with_data(self, path_info: SourceFileInfo, data: bytes):
        """읽은 데이터로 스냅샷 파일 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self._get_snapshot_path(path_info, timestamp)
        
        # 디렉토리 생성
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        # aiofiles로 비동기 파일 쓰기
        try:
            async with aiofiles.open(snapshot_path, "wb") as f:
                await f.write(data)
            logger.info("스냅샷 파일 생성 완료", 
                       filename=path_info.filename,
                       file_size=len(data))
        except Exception as e:
            logger.error("스냅샷 파일 생성 실패", 
                        filename=path_info.filename,
                        exc_info=True)
            raise

    async def create_empty_snapshot_with_info(self, path_info: SourceFileInfo):
        """빈 스냅샷 생성 (삭제 이벤트용) - 파싱된 정보 사용"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_path = self._get_snapshot_path(path_info, timestamp)
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 빈 파일 생성
            async with aiofiles.open(snapshot_path, "wb") as f:
                pass  # 빈 파일
            
            logger.info("빈 스냅샷 생성 완료", filename=path_info.filename)
            
        except Exception as e:
            logger.error("빈 스냅샷 생성 실패", 
                        filename=path_info.filename,
                        exc_info=True)
            raise

    def _get_snapshot_path(self, path_info: SourceFileInfo, timestamp: str) -> Path:
        """스냅샷 파일 경로 생성"""
        snapshot_dir = (settings.SNAPSHOT_BASE / 
                       path_info.class_div / 
                       path_info.hw_name / 
                       path_info.student_id)
        
        # 중첩된 파일 경로 처리
        nested_path = self._get_nested_path(path_info)
        if nested_path:
            snapshot_dir = snapshot_dir / nested_path
            
        return snapshot_dir / f"{timestamp}{path_info.target_file_path.suffix}"

    def _get_nested_path(self, path_info: SourceFileInfo) -> str:
        """과제 디렉토리 이후의 경로를 @로 결합하여 반환"""
        path = Path(path_info.target_file_path)
        hw_index = -1
        for i, part in enumerate(path.parts):
            if part == path_info.hw_name:
                hw_index = i
                break
        
        if hw_index == -1:
            error_msg = f"과제 디렉토리를 찾을 수 없음: {path_info.target_file_path}"
            logger.error(error_msg, 
                        target_path=str(path_info.target_file_path),
                        hw_name=path_info.hw_name)
            raise ValueError(error_msg)
        
        nested_parts = path.parts[hw_index + 1:]
        return '@'.join(nested_parts)