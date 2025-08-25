import asyncio
import os
from typing import Any
from prometheus_client import start_http_server

from .utils.logger import setup_logging, get_logger
from .utils.metrics import loop_heartbeat_task, update_queue_size, active_hosts_update_task
from .collector import Collector
from .pipeline import Pipeline
from .sender import EventSender
from .classifier import ProcessClassifier
from .path_parser import PathParser
from .file_parser import FileParser
from .student_parser import StudentParser
from .config.settings import settings


async def main():
    """메인 애플리케이션 진입점"""
    # 로깅 설정 초기화
    setup_logging(
        log_file_path=settings.LOG_FILE_PATH,
        log_level=settings.LOG_LEVEL,
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT,
    )
    logger = get_logger("main")

    # 프로메테우스 메트릭 서버 시작
    start_http_server(settings.METRICS_PORT)
    logger.info("프로메테우스 메트릭 서버 시작", port=settings.METRICS_PORT)

    # 큐 생성
    queue: asyncio.Queue = asyncio.Queue(maxsize=4096)

    # BPF 프로그램 경로 설정
    program_path = os.path.join(os.path.dirname(__file__), "bpf.c")


    # 컴포넌트 생성
    collector = Collector.start(
        event_queue=queue,
        loop=asyncio.get_running_loop(),
        program_path=program_path,
        page_cnt=64,
        poll_timeout_ms=100,
    )
    sender = EventSender(base_url=settings.API_SERVER)

    classifier = ProcessClassifier()
    path_parser = PathParser()
    file_parser = FileParser()
    student_parser = StudentParser()
    pipeline = Pipeline(classifier, path_parser, file_parser, student_parser)

    # 하트비트 태스크 시작
    heartbeat_task = asyncio.create_task(loop_heartbeat_task())
    
    # 활성 호스트 업데이트 태스크 시작
    active_hosts_task = asyncio.create_task(active_hosts_update_task())

    try:
        logger.info("파이프라인 시작")

        while True:
            try:
                # 큐 사이즈 메트릭 업데이트
                update_queue_size(queue.qsize())
                
                # 큐에서 ProcessStruct 데이터 가져오기
                process_struct = await queue.get()
                # ProcessStruct → Event 변환
                event = await pipeline.pipeline(process_struct)
                if event:
                    await sender.send_event(event)

                queue.task_done()

            except Exception as e:
                logger.error("파이프라인 변환 실패", exc_info=True)

    except KeyboardInterrupt:
        logger.info("종료 신호 수신")
    finally:
        logger.info("프로세스 모니터 종료 중...")
        
        # 하트비트 태스크 정리
        try:
            heartbeat_task.cancel()
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("하트비트 태스크 정리 중 오류", exc_info=True)
        
        # 활성 호스트 태스크 정리
        try:
            active_hosts_task.cancel()
            await active_hosts_task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("활성 호스트 태스크 정리 중 오류", exc_info=True)
        
        if collector:
            collector.stop()
        logger.info("프로세스 모니터 종료 완료")
