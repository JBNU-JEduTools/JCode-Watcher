"""이벤트 큐 유틸리티"""
import asyncio
from typing import Tuple
from ..config.settings import Config

class EventQueue:
    """파일 시스템 이벤트를 비동기적으로 처리하기 위한 간단한 큐"""
    
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        """
        Args:
            loop: 사용할 이벤트 루프 (기본값: 현재 실행 중인 루프)
        """
        self.queue = asyncio.Queue(maxsize=Config.QUEUE_SIZE)
        self.loop = loop or asyncio.get_event_loop()
        
    def put_event_threadsafe(self, event_type: str, file_path: str) -> None:
        """외부 스레드에서 이벤트를 큐에 추가
        
        Args:
            event_type: 이벤트 타입 (예: "modified")
            file_path: 이벤트가 발생한 파일 경로
        """
        asyncio.run_coroutine_threadsafe(
            self.queue.put((event_type, file_path)),
            self.loop
        )
            
    async def get_event(self) -> Tuple[str, str]:
        """이벤트를 큐에서 가져오기"""
        event = await self.queue.get()
        self.queue.task_done()
        return event
            
    async def drain(self) -> None:
        """큐 드레인"""
        await self.queue.join() 