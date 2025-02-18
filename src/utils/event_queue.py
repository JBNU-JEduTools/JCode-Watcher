"""이벤트 큐 유틸리티"""
import asyncio
from typing import Tuple
from ..config.settings import Config
from ..utils.logger import get_logger
from .exceptions import QueueError

class EventQueue:
    """이벤트 큐 관리 클래스"""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.queue = asyncio.Queue(maxsize=Config.QUEUE_SIZE)
        self.loop = loop
        self.logger = get_logger(self.__class__.__name__)
        
    def put_event_threadsafe(self, event_type: str, file_path: str) -> None:
        """외부 스레드에서 이벤트를 큐에 추가"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.put_event(event_type, file_path),
                self.loop
            )
            future.result()
        except Exception as e:
            raise QueueError(f"이벤트 큐 추가 실패 (스레드): {e}") from e
            
    async def put_event(self, event_type: str, file_path: str) -> None:
        """비동기 컨텍스트에서 이벤트를 큐에 추가"""
        try:
            await self.queue.put((event_type, file_path))
            self.logger.debug(f"이벤트 큐에 추가됨: {event_type} - {file_path}")
        except asyncio.QueueFull as e:
            raise QueueError("이벤트 큐가 가득 찼습니다") from e
        except Exception as e:
            raise QueueError(f"이벤트 큐 추가 실패: {e}") from e
            
    async def get_event(self) -> Tuple[str, str]:
        """이벤트를 큐에서 가져옴"""
        try:
            event = await self.queue.get()
            self.queue.task_done()
            self.logger.debug(f"이벤트 큐에서 가져옴: {event}")
            return event
        except Exception as e:
            raise QueueError(f"이벤트 큐에서 가져오기 실패: {e}") from e
            
    async def drain(self) -> None:
        """큐의 모든 작업이 완료될 때까지 대기"""
        try:
            await asyncio.wait_for(
                self.queue.join(),
                timeout=5.0
            )
        except asyncio.TimeoutError as e:
            raise QueueError("큐 드레인 시간 초과") from e
        except Exception as e:
            raise QueueError(f"큐 드레인 실패: {e}") from e 