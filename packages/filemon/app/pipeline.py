import asyncio
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo
from app.config.settings import settings
from app.utils.logger import get_logger
from app.snapshot import SnapshotManager

class FilemonPipeline:
    """파일 모니터링 파이프라인"""
    
    def __init__(self, executor: ThreadPoolExecutor, snapshot_manager: SnapshotManager):
        self.executor = executor
        self.snapshot_manager = snapshot_manager
        self.logger = get_logger("pipeline")
        
    async def process_event(self, event: FilemonEvent):
        """이벤트를 처리하는 단일 통합 흐름"""
        try:
            # 삭제 이벤트는 빈 스냅샷 생성
            if event.event_type == "deleted":
                await self.snapshot_manager.create_empty_snapshot(event.target_file_path)
                return
            
            # 수정 이벤트는 통합 처리 흐름
            if event.event_type == "modified":
                # 1. 스레드풀에서 파일 읽기 및 검증
                future = self.executor.submit(self.read_and_verify, event.target_file_path)
                path_info, file_stat, data = await asyncio.wrap_future(future)
                
                # 2. 바로 스냅샷 생성 (비교 없이)
                await self.snapshot_manager.create_snapshot_with_data(path_info, data)
                self.logger.info(f"스냅샷 생성됨 - {path_info.filename}")
                
        except FileNotFoundError:
            self.logger.warning(f"파일이 존재하지 않음 - {event.target_file_path}")
        except RuntimeError as e:
            self.logger.warning(f"파일 읽기 중 변경됨 - {event.target_file_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"이벤트 처리 실패 - 경로: {event.target_file_path}, 오류: {str(e)}")
    
    def read_and_verify(self, target_file_path: str):
        """
        파일을 안전하게 읽고 검증하는 단일 함수
        s1: 파일 메타데이터 캡처
        read: 파일 전체를 메모리에 읽기
        s2: 읽은 뒤 다시 메타데이터 캡처해서 비교
        """
        src = Path(target_file_path)
        if not src.exists():
            raise FileNotFoundError(target_file_path)

        # s1) 파일 오픈 후 최초 stat
        f = open(src, "rb", buffering=0)
        try:
            st_before = os.fstat(f.fileno())

            # read) 메모리로 읽기
            data = f.read()

            # s2) 다시 stat → 읽는 중 변했는지 확인
            st_after = os.fstat(f.fileno())
            if (st_before.st_size, st_before.st_mtime) != \
               (st_after.st_size, st_after.st_mtime):
                raise RuntimeError("file changed during read")

            return SourceFileInfo.from_target_file_path(Path(target_file_path), settings.WATCH_ROOT), st_after, data
        finally:
            f.close()
    
