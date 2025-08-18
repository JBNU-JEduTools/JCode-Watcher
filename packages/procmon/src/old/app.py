"""프로세스 모니터링 메인 프로그램

BPF 프로그램을 실행하고 이벤트를 처리하는 메인 로직을 구현합니다.
"""

import asyncio
import logging

from src.bpf.collector import BPFCollector
from src.bpf.event import RawBpfEvent
from src.events.models import EventBuilder
from src.process.filter import ProcessFilter
from src.homework.checker import HomeworkChecker
from src.handlers.chain import build_handler_chain
from src.utils.logging import get_logger, set_pid, setup_logging, set_hostname
from src.config.settings import settings
from src.metrics.prometheus import PrometheusMetrics

class Application:
    def __init__(self):
        # 로깅 초기화
        setup_logging(level=getattr(logging, settings.log_level))
        self.logger = get_logger(__name__)
        
        # 애플리케이션 컴포넌트 초기화
        self.event_queue = asyncio.Queue()
        self.collector = None
        self.handler_chain = None
        self.is_running = False
        self.metrics = PrometheusMetrics()

    async def handle_event(self, event: RawBpfEvent):
        """실제 이벤트 처리"""
        try:
            set_pid(event.pid)
            set_hostname(event.hostname)
            
            self.logger.debug(f"[이벤트 수신] 실행 파일: {event.binary_path}")
            builder = EventBuilder(event)
            result = await self.handler_chain.handle(builder)
            if result:
                self.logger.info(f"[이벤트 처리 완료] 타입: {result.process.type if result.process else 'Unknown'}")
        finally:
            set_pid(None)
            set_hostname(None)

    async def process_events(self):
        """이벤트 처리 루프 - 동시 처리 지원"""
        while self.is_running:
            event = await self.event_queue.get()
            asyncio.create_task(self.handle_event(event))
            self.event_queue.task_done()

    async def start(self):
        """애플리케이션 시작"""
        try:
            self.logger.info("[시작] 프로세스 모니터링 시작")
            
            # 프로메테우스 메트릭 서버 시작
            self.logger.debug("[초기화] 프로메테우스 메트릭 서버 시작")
            self.metrics.start_metrics_server()
            self.logger.debug("[초기화] 프로메테우스 메트릭 서버 시작 완료")
            
            # BPF 컬렉터 초기화
            self.logger.debug("[초기화] BPF 컬렉터 초기화 시작")
            self.collector = BPFCollector(self.event_queue)
            self.collector.load_program()
            self.collector.start_polling()
            self.logger.debug("[초기화] BPF 컬렉터 초기화 완료")
            
            # 핸들러 체인 구성
            self.logger.debug("[초기화] 핸들러 체인 구성 시작")
            homework_checker = HomeworkChecker()
            process_filter = ProcessFilter(homework_checker)
            self.handler_chain = build_handler_chain(
                process_filter=process_filter,
                homework_checker=homework_checker
            )
            self.logger.debug("[초기화] 핸들러 체인 구성 완료")
            
            # 이벤트 처리 시작
            self.is_running = True
            self.logger.info("[실행] 이벤트 처리 시작")
            await self.process_events()
            
        except KeyboardInterrupt:
            self.logger.info("[종료] 키보드 인터럽트")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """애플리케이션 종료"""
        self.is_running = False
        if self.collector:
            self.logger.debug("[종료] BPF 컬렉터 정리 시작")
            self.collector.stop_polling()
            await self.event_queue.join()
            self.logger.debug("[종료] BPF 컬렉터 정리 완료")
        self.logger.info("[종료] 프로그램 종료")

if __name__ == "__main__":
    app = Application()
    asyncio.run(app.start()) 