"""파일 시스템 감시 애플리케이션

파일 시스템 변경을 감지하고 스냅샷을 생성하는 애플리케이션입니다.
"""
import sys
import asyncio
import signal
from pathlib import Path
from typing import Union
from watchdog.observers import Observer

from .utils.logger import get_logger
from .snapshot import SnapshotStorage
from .api import ApiClient
from .source_code_path import SourceCodePath
from .source_code_handler import SourceCodeEventHandler
from .source_code_processor import SourceCodeProcessor
from .utils.event_queue import EventQueue
from .config.settings import Config

logger = get_logger(__name__)

async def cleanup(observer: Observer, api_client: Union[ApiClient, None]) -> None:
    """프로그램 종료 시 정리 작업 수행
    
    Args:
        observer: 파일 시스템 감시자
        api_client: API 클라이언트 (연결되지 않은 경우 None)
    """
    logger.info("종료 요청 수신")
    observer.stop()
    if api_client:
        await api_client.disconnect()
    observer.join()
    logger.info("정리 작업 완료")

def setup_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    observer: Observer,
    api_client: Union[ApiClient, None]
) -> None:
    """시그널 핸들러 설정
    
    Args:
        loop: 이벤트 루프
        observer: 파일 시스템 감시자
        api_client: API 클라이언트
    """
    def handle_signal() -> None:
        """시그널 수신 시 정리 작업 태스크 생성"""
        asyncio.create_task(cleanup(observer, api_client))
        
    loop.add_signal_handler(signal.SIGINT, handle_signal)
    loop.add_signal_handler(signal.SIGTERM, handle_signal)

async def main() -> None:
    """메인 실행 함수"""
    observer = None
    api_client = None
    
    try:
        # 이벤트 루프 획득
        loop = asyncio.get_running_loop()
        
        # 초기화
        event_queue = EventQueue(loop)
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
            logger.debug(f"감시 핸들러 등록: {directory}")
            
        observer.start()
        logger.info(f"소스코드 감시 시작 (대상: {len(directories)}개)")
        
        # API 클라이언트 초기화
        api_client = ApiClient()
        await api_client.connect()
        
        # 시그널 핸들러 설정
        setup_signal_handlers(loop, observer, api_client)
        
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
