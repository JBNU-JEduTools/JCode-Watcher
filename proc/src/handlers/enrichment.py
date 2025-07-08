"""메타데이터 보강 핸들러

이벤트에 메타데이터(타임스탬프, 분반, 학번 등)를 추가합니다.
"""

from datetime import datetime, timezone
from typing import Optional

from .base import EventHandler
from ..events.models import EventBuilder, EventMetadata
from ..utils.logging import get_logger

class EnrichmentHandler(EventHandler[EventBuilder, EventBuilder]):
    """메타데이터 보강 핸들러"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        
    async def handle(self, builder: EventBuilder) -> Optional[EventBuilder]:
        """이벤트 처리
        
        Args:
            builder: 이벤트 빌더l
            
        Returns:
            처리된 이벤트 빌더 또는 None
        """
        try:
            # 초기 이벤트 정보 (INFO)
            self.logger.info(
                f"이벤트 수신: "
                f"binary={builder.base.binary_path}, "
                f"args={builder.base.args}, "
                f"cwd={builder.base.cwd}, "
                f"exit_code={builder.base.exit_code}"
            )
            
            self.logger.debug("메타데이터 보강 시작")
            
            # 호스트네임을 대시(-)로 분리
            parts = builder.base.hostname.split('-')

            
            # 최소 4개 부분이 필요: 접두사-과목명-분반-학번[-해시]
            if len(parts) < 4:
                # 핸들링 체인 종료 조건 (INFO)
                self.logger.info(f"호스트네임 형식 불일치로 처리 중단: {builder.base.hostname}")
                return None
            
            self.logger.debug(f"호스트네임 분리 결과: {parts}")
            
            # 과목명-분반을 class_div로 합침
            class_div = f"{parts[1]}-{parts[2]}"
            student_id = parts[3]
            
            builder.metadata = EventMetadata(
                class_div=class_div,
                student_id=student_id,
                timestamp=datetime.now(timezone.utc)
            )
            
            # 처리 성공 (DEBUG)
            self.logger.debug(
                f"메타데이터 보강 완료: "
                f"class_div={builder.metadata.class_div}, "
                f"student_id={builder.metadata.student_id}"
            )
            
            return await self._handle_next(builder)
            
        except Exception as e:
            self.logger.error(f"메타데이터 보강 실패: {str(e)}")
            return None