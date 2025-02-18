"""이벤트 큐 유틸리티"""
import asyncio
from ..config.settings import Config
from ..utils.logger import get_logger

class EventQueue:
    """이벤트 큐 관리 클래스"""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.queue = asyncio.Queue(maxsize=Config.QUEUE_SIZE)
        self.loop = loop
        self.logger = get_logger(self.__class__.__name__)
        
    def put_event_threadsafe(self, event_type: str, file_path: str) -> None:
        """외부 스레드에서 이벤트를 큐에 추가"""
        try:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait,
                (event_type, file_path)
            )
            self.logger.debug(f"이벤트 큐에 추가됨 (스레드): {event_type} - {file_path}")
        except asyncio.QueueFull:
            self.logger.warning("이벤트 큐가 가득 찼습니다.")
            
    async def put_event(self, event_type: str, file_path: str) -> None:
        """비동기 컨텍스트에서 이벤트를 큐에 추가"""
        try:
            await self.queue.put((event_type, file_path))
            self.logger.debug(f"이벤트 큐에 추가됨 (비동기): {event_type} - {file_path}")
        except asyncio.QueueFull:
            self.logger.warning("이벤트 큐가 가득 찼습니다.")
            
    async def get_event(self) -> tuple[str, str]:
        """이벤트를 큐에서 가져옴"""
        event = await self.queue.get()
        self.logger.debug(f"이벤트 큐에서 가져옴: {event}")
        return event
        
    def task_done(self) -> None:
        """이벤트 처리 완료 표시"""
        self.queue.task_done()
        self.logger.debug("이벤트 처리 완료") 