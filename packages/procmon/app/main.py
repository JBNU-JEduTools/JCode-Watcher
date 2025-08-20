import asyncio
from .logger import logger
import os
from typing import Any

from .collector import Collector
from .pipeline import ProcessEventPipeline
from .settings import settings


async def main():
    """메인 애플리케이션 진입점"""
    
    
    # 큐 생성
    queue: asyncio.Queue = asyncio.Queue(maxsize=4096)
    
    # BPF 프로그램 경로 설정
    program_path = get_bpf_program_path()
    logger.info(f"BPF 프로그램 경로: {program_path}")
    logger.info(f"로그 레벨: {settings.LOG_LEVEL}")
    
    # 컴포넌트 생성
    collector = create_collector(queue, program_path)
    pipeline = ProcessEventPipeline(queue)
    
    try:
        logger.info("프로세스 모니터 시작")
        
        # Pipeline만 실행 (Collector는 이미 백그라운드에서 실행 중)
        await pipeline.start()
        
    except KeyboardInterrupt:
        logger.info("종료 신호 수신")
    finally:
        logger.info("프로세스 모니터 종료 중...")
        if collector:
            collector.stop()
        logger.info("프로세스 모니터 종료 완료")


def get_bpf_program_path() -> str:
    """BPF 프로그램 경로 반환"""
    return os.path.join(os.path.dirname(__file__), "bpf.c")


def create_collector(queue: asyncio.Queue, program_path: str) -> Collector:
    """Collector 인스턴스 생성"""
    return Collector.start(
        event_queue=queue,
        loop=asyncio.get_running_loop(),
        program_path=program_path,
        page_cnt=64,
        poll_timeout_ms=100,
    )
