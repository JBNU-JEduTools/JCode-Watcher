from typing import Optional

from .base import EventHandler
from ..events.models import EventBuilder, ProcessTypeInfo
from ..process.filter import ProcessFilter
from ..process.types import ProcessType
from ..utils.logging import get_logger

class ProcessTypeHandler(EventHandler[EventBuilder, EventBuilder]):
    """프로세스 타입 감지 핸들러
    
    실행된 프로세스의 타입을 감지하여 이벤트에 추가합니다.
    """
    
    def __init__(self, process_filter: ProcessFilter):
        """초기화
        
        Args:
            process_filter: 프로세스 타입 결정을 위한 필터
        """
        super().__init__()
        self.logger = get_logger(__name__)
        self.process_filter = process_filter
    
    async def handle(self, builder: EventBuilder) -> Optional[EventBuilder]:
        """이벤트 처리
        
        Args:
            builder: 이벤트 빌더
            
        Returns:
            처리된 이벤트 빌더 또는 None
        """
        try:
            self.logger.debug("프로세스 타입 감지 시작")
            process_type = self.process_filter.get_process_type(builder.base.binary_path)
            
            if process_type == ProcessType.UNKNOWN:
                # 핸들링 체인 종료 조건 (INFO)
                self.logger.debug(f"지원하지 않는 프로세스 타입으로 처리 중단: {builder.base.binary_path}")
                return None
                
            builder.process = ProcessTypeInfo(type=process_type)
            # 처리 성공 (DEBUG)
            self.logger.debug(f"프로세스 타입 감지 완료: type={process_type}")
            
            return await self._handle_next(builder)
            
        except Exception as e:
            self.logger.error(f"프로세스 타입 감지 실패: {str(e)}")
            return None 