"""
파일 시스템 감시 메인 모듈
watchdog과 asyncio를 사용하여 특정 디렉토리의 파일 변경을 감시
"""
import asyncio
from .app import Application
from .utils.logger import setup_logger, get_logger
from .utils.exceptions import (
    WatcherError, ApiError, MetadataError, 
    StorageError, QueueError
)

# 로깅 설정
setup_logger()
logger = get_logger(__name__)

async def main() -> None:
    """메인 함수"""
    try:
        app = Application()
        if await app.setup():
            await app.start()
    except (ApiError, MetadataError) as e:
        logger.error(f"API/메타데이터 처리 오류: {e}")
    except StorageError as e:
        logger.error(f"스토리지 처리 오류: {e}")
    except QueueError as e:
        logger.error(f"이벤트 큐 처리 오류: {e}")
    except WatcherError as e:
        logger.error(f"감시자 처리 오류: {e}")
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
    finally:
        if 'app' in locals():
            try:
                await app.shutdown()
            except Exception as e:
                logger.error(f"종료 중 오류 발생: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
