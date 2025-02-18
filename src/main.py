"""파일 시스템 감시 애플리케이션

파일 시스템 변경을 감지하고 스냅샷을 생성하는 애플리케이션입니다.
"""
import sys
import asyncio
import signal
from pathlib import Path
from watchdog.observers import Observer

from .snapshot import SnapshotStorage
from .api import ApiClient
from .homework_path import HomeworkPath
from .homework_handler import HomeworkHandler
from .homework_processor import HomeworkProcessor
from .utils.event_queue import EventQueue
from .utils.logger import setup_logger, get_logger
from .config.settings import Config

# 로깅 설정
setup_logger()
logger = get_logger(__name__)

async def main() -> None:
    """메인 함수
    
    파일 시스템 감시 및 스냅샷 생성을 수행합니다.
    """
    observer = None
    
    try:
        # 초기화
        loop = asyncio.get_running_loop()
        event_queue = EventQueue(loop)
        path_manager = HomeworkPath(Config.BASE_PATH)
        handler = HomeworkHandler(path_manager, event_queue)
        storage = SnapshotStorage(Path(Config.SNAPSHOT_PATH))
        
        # 감시 디렉토리 설정
        directories = path_manager.find_homework_dirs()
        if not directories:
            logger.error("감시할 디렉토리가 없습니다")
            return
            
        # 감시 시작
        observer = Observer()
        for directory in directories:
            observer.schedule(handler, directory, recursive=True)
        observer.start()
        
        # API 클라이언트 및 이벤트 처리
        async with ApiClient(Config.API_URL) as api_client:
            # 종료 시그널 설정
            def handle_stop(*_):
                observer.stop()
                for task in asyncio.all_tasks():
                    task.cancel()
                    
            signal.signal(signal.SIGINT, handle_stop)
            signal.signal(signal.SIGTERM, handle_stop)
            
            # 과제 처리 시작
            processor = HomeworkProcessor(event_queue, handler, storage, api_client)
            await processor.process()
            
    except asyncio.CancelledError:
        logger.info("프로그램 종료")
    except Exception as e:
        logger.error(f"실행 실패: {e}")
        sys.exit(1)
    finally:
        if observer and observer.is_alive():
            observer.stop()
            observer.join()
            
if __name__ == "__main__":
    asyncio.run(main())
