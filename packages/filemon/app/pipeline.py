import asyncio
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from watchdog.events import FileSystemEvent
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo
from app.source_path_parser import SourcePathParser
from app.path_filter import PathFilter
from app.config.settings import settings
from app.utils.logger import get_logger
from app.snapshot import SnapshotManager
from app.sender import SnapshotSender

class FilemonPipeline:
    """파일 모니터링 파이프라인"""
    
    def __init__(self, executor: ThreadPoolExecutor, snapshot_manager: SnapshotManager, snapshot_sender: SnapshotSender, parser: SourcePathParser, path_filter: PathFilter):
        self.executor = executor
        self.snapshot_manager = snapshot_manager
        self.snapshot_sender = snapshot_sender
        self.parser = parser
        self.path_filter = path_filter
        self.logger = get_logger("pipeline")
        
    async def process_event(self, raw_event: FileSystemEvent):
        """raw 파일시스템 이벤트를 처리하는 통합 흐름"""
        try:
            if raw_event.event_type == "moved":
                await self._handle_moved_event(raw_event)
            elif raw_event.event_type == "deleted":
                await self._handle_deleted_event(raw_event)
            elif raw_event.event_type == "modified":
                await self._handle_modified_event(raw_event)
            else:
                self.logger.warning(f"알 수 없는 이벤트 타입: {raw_event.event_type}")
                
        except Exception as e:
            self.logger.error(f"이벤트 처리 실패 - 타입: {raw_event.event_type}, "
                            f"경로: {raw_event.src_path}, 오류: {str(e)}", exc_info=True)

    async def _handle_moved_event(self, event: FileSystemEvent):
        """moved 이벤트 처리 - delete + modify로 분해"""
        src_path = event.src_path
        dest_path = getattr(event, 'dest_path', None)
        
        if not dest_path:
            self.logger.warning("moved 이벤트에 dest_path가 없음", src_path=src_path)
            return
            
        try:
            # 1. src_path 삭제 처리
            parsed_data = self.parser.parse(Path(src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(src_path))
            
            await self.snapshot_manager.create_empty_snapshot_with_info(source_info)
            await self.snapshot_sender.register_snapshot(source_info, 0)
            self.logger.info(f"moved 삭제 처리 완료 - {source_info.filename}")
            
            # 2. dest_path 생성 처리
            if not os.path.exists(dest_path):
                self.logger.warning("moved 대상 파일이 존재하지 않음", 
                                  src_path=src_path, dest_path=dest_path)
                return
                
            file_size = os.path.getsize(dest_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                self.logger.warning("moved 대상 파일 크기 초과", dest_path=dest_path, 
                                  file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                return
            
            parsed_data = self.parser.parse(Path(dest_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(dest_path))
            
            # 파일 읽기 및 스냅샷 생성
            future = self.executor.submit(self.read_and_verify, dest_path)
            file_stat, data = await asyncio.wrap_future(future)
            
            await self.snapshot_manager.create_snapshot_with_data(source_info, data)
            api_success = await self.snapshot_sender.register_snapshot(source_info, len(data))
            
            if api_success:
                self.logger.info(f"moved 생성 처리 완료 - {source_info.filename}")
            else:
                self.logger.warning(f"moved 생성 API 등록 실패 - {source_info.filename}")
                
        except OSError as e:
            self.logger.debug("moved 이벤트 처리 중 OSError 발생", 
                            src_path=src_path, dest_path=dest_path, error=str(e))
        except Exception as e:
            self.logger.error("moved 이벤트 처리 실패", 
                            src_path=src_path, dest_path=dest_path, error=str(e), exc_info=True)

    async def _handle_deleted_event(self, event: FileSystemEvent):
        """deleted 이벤트 처리"""
        try:
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            
            await self.snapshot_manager.create_empty_snapshot_with_info(source_info)
            await self.snapshot_sender.register_snapshot(source_info, 0)
            self.logger.info(f"삭제 처리 완료 - {source_info.filename}")
            
        except Exception as e:
            self.logger.error("deleted 이벤트 처리 실패", 
                            src_path=event.src_path, error=str(e), exc_info=True)

    async def _handle_modified_event(self, event: FileSystemEvent):
        """modified 이벤트 처리"""
        try:
            file_size = os.path.getsize(event.src_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                self.logger.warning("파일 크기 초과", src_path=event.src_path, 
                                  file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                return
            
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            
            # 파일 읽기 및 스냅샷 생성
            future = self.executor.submit(self.read_and_verify, event.src_path)
            file_stat, data = await asyncio.wrap_future(future)
            
            await self.snapshot_manager.create_snapshot_with_data(source_info, data)
            api_success = await self.snapshot_sender.register_snapshot(source_info, len(data))
            
            if api_success:
                self.logger.info(f"수정 처리 완료 - {source_info.filename}")
            else:
                self.logger.warning(f"수정 API 등록 실패 - {source_info.filename}")
                
        except FileNotFoundError:
            self.logger.warning(f"파일이 존재하지 않음 - {event.src_path}")
        except RuntimeError as e:
            self.logger.warning(f"파일 읽기 중 변경됨 - {event.src_path}: {str(e)}")
        except OSError as e:
            self.logger.debug("modified 이벤트 처리 중 OSError 발생", 
                            src_path=event.src_path, error=str(e))
        except Exception as e:
            self.logger.error("modified 이벤트 처리 실패", 
                            src_path=event.src_path, error=str(e), exc_info=True)
    
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

            return st_after, data
        finally:
            f.close()
    
