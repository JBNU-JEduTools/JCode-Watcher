from abc import ABC, abstractmethod
from typing import Optional, Generic, TypeVar, Any
import logging

InputType = TypeVar('InputType')
OutputType = TypeVar('OutputType')

class EventHandler(Generic[InputType, OutputType], ABC):
    """이벤트 핸들러 기본 클래스
    
    책임 연쇄 패턴의 핸들러를 정의합니다.
    각 핸들러는 이벤트를 받아서 처리하고, 다음 핸들러로 전달할 수 있습니다.
    """
    def __init__(self):
        self._next_handler: Optional[EventHandler] = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def set_next(self, handler: 'EventHandler') -> 'EventHandler':
        """다음 핸들러 설정
        
        Args:
            handler: 다음 핸들러
            
        Returns:
            다음 핸들러 (체이닝을 위해)
        """
        self._next_handler = handler
        return handler
    
    @abstractmethod
    async def handle(self, event: InputType) -> Optional[OutputType]:
        """이벤트 처리
        
        Args:
            event: 처리할 이벤트
            
        Returns:
            처리된 이벤트 또는 None (처리 중단 시)
        """
        pass

    async def _handle_next(self, event: OutputType) -> Optional[Any]:
        """다음 핸들러로 이벤트 전달
        
        Args:
            event: 다음 핸들러로 전달할 이벤트
            
        Returns:
            다음 핸들러의 처리 결과 또는 None (마지막 핸들러인 경우)
        """
        if self._next_handler:
            return await self._next_handler.handle(event)
        return None 