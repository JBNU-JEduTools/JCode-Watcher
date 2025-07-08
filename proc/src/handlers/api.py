from typing import Optional

from .base import EventHandler
from ..api.client import APIClient
from ..events.models import EventBuilder, Event
from ..process.types import ProcessType

class APIHandler(EventHandler[EventBuilder, EventBuilder]):
    """API 이벤트 핸들러
    
    완성된 이벤트를 API 서버로 전송합니다.
    이벤트 타입에 따라 적절한 엔드포인트로 전송됩니다.
    """
    
    def __init__(self):
        """초기화"""
        super().__init__()
        self.client = APIClient()
    
    async def handle(self, builder: EventBuilder) -> Optional[EventBuilder]:
        """이벤트 처리
        
        Args:
            builder: 이벤트 빌더 (모든 정보가 포함된 상태)
            
        Returns:
            EventBuilder 또는 None (API 전송 실패 시)
        """
        try:
            # 필수 정보 검증
            if not builder.metadata or not builder.homework:
                self.logger.error("전송 실패 - 메타데이터 또는 과제 정보 누락")
                return None
                
            # 이벤트 생성
            event = builder.build()
            
            # 이벤트 타입에 따라 전송
            if event.is_compilation:
                success = await self.client.send_compilation(event)
            elif event.process.type == ProcessType.PYTHON:
                success = await self.client.send_python_execution(event)
            else:
                success = await self.client.send_binary_execution(event)
            
            # API 전송 성공 시 빌더 반환
            return builder if success else None
            
        except Exception as e:
            self.logger.error(f"전송 실패 - API 이벤트 처리 오류: {str(e)}")
            return None 