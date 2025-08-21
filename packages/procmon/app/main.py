import asyncio
from .logger import logger
import os
from typing import Any

from .collector import Collector
from .pipeline import ProcessEventPipeline
from .sender import EventSender
from .settings import settings


async def main():
    """메인 애플리케이션 진입점"""
    # 큐 생성
    queue: asyncio.Queue = asyncio.Queue(maxsize=4096)
    
    # BPF 프로그램 경로 설정
    program_path = os.path.join(os.path.dirname(__file__), "bpf.c")
    logger.info(f"BPF 프로그램 경로: {program_path}")
    logger.info(f"로그 레벨: {settings.LOG_LEVEL}")
    
    # 컴포넌트 생성
    collector = Collector.start(
        event_queue=queue,
        loop=asyncio.get_running_loop(),
        program_path=program_path,
        page_cnt=64,
        poll_timeout_ms=100,
    )
    pipeline = ProcessEventPipeline()
    sender = EventSender(base_url=settings.API_SERVER)
    
    try:
        logger.info("파이프라인 시작")
        
        while True:
            try:
                # 큐에서 ProcessStruct 데이터 가져오기
                process_struct = await queue.get()
                
                # ProcessStruct → Event 변환
                event = await pipeline.pipeline(process_struct)
                
                if event:
                    # Sender로 전송
                    success = await sender.send_event(event)
                    if success:
                        logger.debug(f"이벤트 전송 성공: {event.binary_path}")
                    else:
                        logger.error(f"이벤트 전송 실패: {event.binary_path}")
                else:
                    logger.debug(f"이벤트 필터링됨: {process_struct}")
                
                queue.task_done()
                
            except Exception as e:
                logger.error(f"파이프라인 변환 실패: {e}")
        
    except KeyboardInterrupt:
        logger.info("종료 신호 수신")
    finally:
        logger.info("프로세스 모니터 종료 중...")
        if collector:
            collector.stop()
        logger.info("프로세스 모니터 종료 완료")


