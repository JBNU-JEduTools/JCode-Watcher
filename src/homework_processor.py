"""과제 처리기

과제 파일 변경을 감지하고 스냅샷을 생성하는 메인 처리 흐름을 관리합니다.
"""
import os
from datetime import datetime
from pathlib import Path
import aiofiles
import asyncio

from .snapshot import SnapshotStorage, SnapshotInfo
from .api import ApiClient
from .homework_handler import HomeworkHandler
from .homework_path import HomeworkInfo
from .utils.event_queue import EventQueue
from .utils.logger import get_logger
from .utils.exceptions import FileNotFoundInWorkspaceError

logger = get_logger(__name__)

class HomeworkProcessor:
    """과제 처리기
    
    과제 파일 변경 감지부터 스냅샷 생성, API 등록까지의 전체 처리 흐름을 관리합니다.
    """
    
    def __init__(self, event_queue: EventQueue, handler: HomeworkHandler,
                 storage: SnapshotStorage, api_client: ApiClient):
        """
        Args:
            event_queue: 이벤트 큐
            handler: 과제 파일 이벤트 처리기
            storage: 스냅샷 저장소
            api_client: API 클라이언트
        """
        self.event_queue = event_queue
        self.handler = handler
        self.storage = storage
        self.api_client = api_client
        
    async def _verify_file_changes(self, file_path: str, last_snapshot: Path = None) -> bool:
        """파일 변경 여부 확인
        
        Args:
            file_path: 검사할 파일 경로
            last_snapshot: 마지막 스냅샷 경로 (없으면 None)
            
        Returns:
            bool: 파일이 변경되었으면 True, 아니면 False
            
        Raises:
            FileNotFoundInWorkspaceError: 파일을 찾을 수 없는 경우
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                raise FileNotFoundInWorkspaceError(f"파일을 찾을 수 없습니다: {file_path}")
                
            # 첫 번째 스냅샷이면 변경된 것으로 간주
            if not last_snapshot or not last_snapshot.exists():
                return True
                
            # 파일 크기 비교
            if source_path.stat().st_size != last_snapshot.stat().st_size:
                return True
                
            # 파일 내용 비교
            chunk_size = 8192
            async with aiofiles.open(source_path, 'rb') as f1, \
                       aiofiles.open(last_snapshot, 'rb') as f2:
                while True:
                    chunk1 = await f1.read(chunk_size)
                    chunk2 = await f2.read(chunk_size)
                    if chunk1 != chunk2:
                        return True
                    if not chunk1:  # EOF
                        return False
                        
        except FileNotFoundInWorkspaceError:
            raise
        except Exception as e:
            raise FileNotFoundInWorkspaceError(f"파일 검증 실패: {e}") from e
        
    async def process(self) -> None:
        """과제 처리 루프 실행"""
        while True:
            # 이벤트 대기 (이미 검증된 HomeworkInfo를 받음)
            event_type, homework_info = await self.event_queue.get_event()
            
            try:
                # 파일 존재 및 변경 여부 확인
                snapshot_dir = self.storage._get_snapshot_dir(homework_info)
                last_snapshot = None
                if snapshot_dir.exists():
                    snapshots = list(snapshot_dir.glob("*"))
                    if snapshots:
                        last_snapshot = max(snapshots, key=lambda x: x.stat().st_mtime)
                
                if not await self._verify_file_changes(homework_info.original_path, last_snapshot):
                    logger.debug(f"No changes detected: {homework_info.original_path}")
                    continue
                    
                # 스냅샷 생성
                if not (snapshot_path := await self.storage.create(
                    homework_info.original_path, 
                    homework_info
                )):
                    continue
                    
                # API 서버에 등록
                await self.api_client.register_snapshot({
                    "class_div": homework_info.class_div,
                    "homework_dir": homework_info.hw_dir,
                    "student_id": homework_info.student_id,
                    "filename": homework_info.filename,
                    "original_path": homework_info.original_path,
                    "snapshot_path": str(snapshot_path),
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "file_size": Path(homework_info.original_path).stat().st_size
                })
                
            except FileNotFoundInWorkspaceError as e:
                logger.warning(str(e))
            except Exception as e:
                logger.error(f"과제 처리 중 오류 발생: {e}", exc_info=True)
                raise 