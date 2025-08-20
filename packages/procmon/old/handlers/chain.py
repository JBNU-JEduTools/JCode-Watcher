"""핸들러 체인 구성

이벤트 처리를 위한 핸들러 체인을 구성합니다.
각 핸들러는 책임 연쇄 패턴에 따라 순차적으로 이벤트를 처리합니다.

핸들러 체인 순서:
1. ProcessTypeHandler: 프로세스 타입 감지 (GCC, CLANG, PYTHON 등)
2. EnrichmentHandler: 메타데이터 추가 (타임스탬프, 분반, 학번 등)
3. HomeworkHandler: 과제 정보 추가 (과제 디렉토리, 소스 파일)
4. APIHandler: API 서버로 이벤트 전송
"""

from typing import Optional
from .base import EventHandler
from .process import ProcessTypeHandler
from .enrichment import EnrichmentHandler
from .homework import HomeworkHandler
from .api import APIHandler
from ..events.models import EventBuilder
from ..process.filter import ProcessFilter
from ..homework.checker import HomeworkChecker

def build_handler_chain(
    process_filter: ProcessFilter,
    homework_checker: HomeworkChecker,
) -> EventHandler[EventBuilder, EventBuilder]:
    """핸들러 체인을 구성합니다.
    
    Args:
        process_filter: 프로세스 타입 결정을 위한 필터
        homework_checker: 과제 디렉토리 체크를 위한 체커
        
    Returns:
        첫 번째 핸들러 (체인의 시작점)
        
    Note:
        핸들러 체인 순서:
        1. ProcessTypeHandler: 프로세스 타입 감지
        2. EnrichmentHandler: 메타데이터 추가
        3. HomeworkHandler: 과제 정보 추가
        4. APIHandler: API 서버로 이벤트 전송
    """
    # 핸들러 인스턴스 생성
    process_handler = ProcessTypeHandler(process_filter)
    enrichment_handler = EnrichmentHandler()
    homework_handler = HomeworkHandler(homework_checker)
    api_handler = APIHandler()
    
    # 체인 연결
    process_handler.set_next(enrichment_handler)
    enrichment_handler.set_next(homework_handler)
    homework_handler.set_next(api_handler)
    
    return process_handler