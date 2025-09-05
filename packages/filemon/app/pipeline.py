import asyncio
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from watchdog.events import FileSystemEvent
from app.models.filemon_event import FilemonEvent
from app.models.source_file_info import SourceFileInfo
from app.source_path_parser import SourcePathParser
from app.source_path_filter import PathFilter
from app.config.settings import settings
from app.utils.logger import get_logger
from app.snapshot import SnapshotManager
from app.sender import SnapshotSender
from app.utils.metrics import record_file_size_exceeded

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
            if raw_event.event_type == "deleted":
                await self._handle_deleted_event(raw_event)
            elif raw_event.event_type == "modified":
                await self._handle_modified_event(raw_event)
            else:
                self.logger.warning("알 수 없는 이벤트 타입", event_type=raw_event.event_type, src_path=raw_event.src_path)
                
        except Exception as e:
            self.logger.error("이벤트 처리 실패",
                            event_type=raw_event.event_type,
                            src_path=raw_event.src_path,
                            error_type=type(e).__name__,
                            exc_info=True)


    async def _handle_deleted_event(self, event: FileSystemEvent):
        """deleted 이벤트 처리"""
        try:
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            
            await self.snapshot_manager.create_empty_snapshot_with_info(source_info)
            await self.snapshot_sender.register_snapshot(source_info, 0)
            self.logger.info("삭제 처리 완료",
                           filename=source_info.filename,
                           class_div=source_info.class_div,
                           hw_name=source_info.hw_name,
                           student_id=source_info.student_id)
            
        except Exception as e:
            self.logger.error("deleted 이벤트 처리 실패", 
                            src_path=event.src_path, exc_info=True)

    async def _handle_modified_event(self, event: FileSystemEvent):
        """modified 이벤트 처리"""
        try:
            file_size = os.path.getsize(event.src_path)
            if file_size > settings.MAX_CAPTURABLE_FILE_SIZE:
                self.logger.warning("파일 크기 초과", src_path=event.src_path, 
                                  file_size=file_size, max_size=settings.MAX_CAPTURABLE_FILE_SIZE)
                record_file_size_exceeded()
                return
            
            parsed_data = self.parser.parse(Path(event.src_path))
            source_info = SourceFileInfo.from_parsed_data(parsed_data, Path(event.src_path))
            
            # 파일 읽기 및 스냅샷 생성
            future = self.executor.submit(self.read_and_verify, event.src_path)
            file_stat, data = await asyncio.wrap_future(future)
            
            await self.snapshot_manager.create_snapshot_with_data(source_info, data)
            api_success = await self.snapshot_sender.register_snapshot(source_info, len(data))
            
            if api_success:
                self.logger.info("수정 처리 완료",
                                filename=source_info.filename,
                                class_div=source_info.class_div,
                                hw_name=source_info.hw_name,
                                student_id=source_info.student_id,
                                file_size=len(data))
            else:
                self.logger.warning("수정 API 등록 실패",
                                  filename=source_info.filename,
                                  class_div=source_info.class_div,
                                  hw_name=source_info.hw_name,
                                  student_id=source_info.student_id)
                
        except FileNotFoundError:
            self.logger.warning("파일이 존재하지 않음", src_path=event.src_path)
        except RuntimeError as e:
            self.logger.warning("파일 읽기 중 변경됨",
                              src_path=event.src_path,
                              exc_info=True)
        except OSError as e:
            self.logger.debug("modified 이벤트 처리 중 OSError 발생", 
                            src_path=event.src_path, exc_info=True)
        except Exception as e:
            self.logger.error("modified 이벤트 처리 실패", 
                            src_path=event.src_path, exc_info=True)
    
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