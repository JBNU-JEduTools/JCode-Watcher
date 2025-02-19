"""파일 시스템 감시 애플리케이션

파일 시스템 변경을 감지하고 스냅샷을 생성하는 애플리케이션입니다.
"""
import sys
import asyncio
import signal
from pathlib import Path
from watchdog.observers import Observer
import logging

from .snapshot import SnapshotStorage
from .api import ApiClient
from .source_code_path import SourceCodePath
from .source_code_handler import SourceCodeEventHandler
from .source_code_processor import SourceCodeProcessor
from .utils.event_queue import EventQueue
from .config.settings import Config

logger = logging.getLogger(__name__)

async def main() -> None:
    """메인 실행 함수"""
    observer = None
    api_client = None
    
    try:
        # 초기화
        event_queue = EventQueue(asyncio.get_running_loop())
        path_manager = SourceCodePath(Config.BASE_PATH)
        storage = SnapshotStorage(Path(Config.SNAPSHOT_PATH))
        
        # 감시 디렉토리 설정
        directories = path_manager.find_source_dirs()
        if not directories:
            logger.warning(f"감시할 소스코드 디렉토리 없음: {Config.BASE_PATH}")
            return
            
        # 감시 시작
        observer = Observer()
        for directory in directories:
            handler = SourceCodeEventHandler(path_manager, event_queue)
            observer.schedule(handler, directory, recursive=True)
            
        observer.start()
        logger.info(f"소스코드 감시 시작 (대상: {len(directories)}개)")
        
        # 시그널 핸들러 설정
        def handle_stop(*_):
            observer.stop()
            for task in asyncio.all_tasks():
                task.cancel()
                
        signal.signal(signal.SIGINT, handle_stop)
        signal.signal(signal.SIGTERM, handle_stop)
        
        # API 클라이언트 초기화
        api_client = ApiClient(Config.API_URL)
        await api_client.connect()
        
        # 이벤트 처리 시작
        processor = SourceCodeProcessor(event_queue, storage, api_client)
        await processor.run()
                
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
    finally:
        if api_client:
            await api_client.disconnect()
        if observer:
            observer.stop()
            observer.join()

if __name__ == "__main__":
    asyncio.run(main())
