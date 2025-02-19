"""파일 시스템 감시 애플리케이션

파일 시스템 변경을 감지하고 스냅샷을 생성하는 애플리케이션입니다.
"""
import sys
import asyncio
import signal
from pathlib import Path
from watchdog.observers import Observer
import logging
from aiohttp import ClientError

from .snapshot import SnapshotStorage
from .api import ApiClient
from .homework_path import HomeworkPath
from .homework_handler import HomeworkHandler
from .homework_processor import HomeworkProcessor
from .utils.event_queue import EventQueue
from .config.settings import Config

# 로거 설정
logger = logging.getLogger(__name__)

async def main() -> None:
    """메인 함수"""
    observer = None
    
    try:
        # 초기화
        loop = asyncio.get_running_loop()
        event_queue = EventQueue(loop)
        path_manager = HomeworkPath(Config.BASE_PATH)
        handler = HomeworkHandler(path_manager, event_queue)
        storage = SnapshotStorage(Path(Config.SNAPSHOT_PATH))
        logger.info("시스템 초기화 완료")
        
        # 감시 디렉토리 설정
        directories = path_manager.find_homework_dirs()
        if not directories:
            logger.warning(f"감시할 과제 디렉토리 없음: {Config.BASE_PATH}")
            return
            
        # 감시 시작
        observer = Observer()
        for directory in directories:
            observer.schedule(handler, directory, recursive=True)
            logger.debug(f"감시 디렉토리 추가: {directory}")
            
        observer.start()
        logger.info(f"과제 감시 시작 (대상: {len(directories)}개)")
        
        # API 클라이언트 및 이벤트 처리
        async with ApiClient(Config.API_URL) as api_client:
            def handle_stop(*_):
                observer.stop()
                for task in asyncio.all_tasks():
                    task.cancel()
                    
            signal.signal(signal.SIGINT, handle_stop)
            signal.signal(signal.SIGTERM, handle_stop)
            
            processor = HomeworkProcessor(event_queue, storage, api_client)
            await processor.run()
            
    except asyncio.CancelledError:
        logger.info("프로그램 종료 요청")
    except Exception as e:
        logger.error(f"치명적 오류 발생: {str(e)}")
        sys.exit(1)
    finally:
        if observer and observer.is_alive():
            observer.stop()
            observer.join()
            logger.info("감시 작업 종료")
            
if __name__ == "__main__":
    asyncio.run(main())
