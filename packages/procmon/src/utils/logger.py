import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import structlog
import structlog.contextvars as ctx


# 우리 앱 전용 최상위 로거 네임스페이스
APP_LOGGER_NAME = "procmon"


def setup_logging(
    log_file_path: str,
    log_level: str,
    max_bytes: int,
    backup_count: int,
):
    """
    structlog와 contextvars를 활용한 간결하고 Pythonic한 로깅 설정.
    - 콘솔: 가독성 좋은 컬러 출력
    - 파일: 구조화된 JSON 출력 (RotatingFileHandler 사용)
    - contextvars: 요청/작업 컨텍스트 자동 병합
    """
    # 1. 로그 파일 디렉토리 생성
    log_dir = os.path.dirname(log_file_path)
    os.makedirs(log_dir, exist_ok=True)

    # 2. 표준 로깅 설정
    # 루트 로거는 WARNING으로 설정하여 대부분의 라이브러리를 조용하게 만듭니다.
    logging.basicConfig(
        level=logging.CRITICAL,
        handlers=[],  # 기본 핸들러 추가 방지
    )

    # 우리 앱 로거는 원하는 레벨로 설정합니다.
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.setLevel(log_level)
    app_logger.propagate = False  # 루트 로거로 전파 방지

    # 2.1. 콘솔 핸들러 설정 (가독성 좋은 컬러 출력)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    app_logger.addHandler(console_handler)

    # 2.2. 파일 핸들러 설정 (구조화된 JSON 출력, 용량 기반 로테이션)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(ensure_ascii=False),
    )

    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)
    app_logger.addHandler(file_handler)

    # 3. structlog 설정
    structlog.configure(
        processors=[
            ctx.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """애플리케이션 네임스페이스에 맞는 structlog 로거를 가져옵니다."""
    full_name = f"{APP_LOGGER_NAME}.{name}"
    return structlog.get_logger(full_name)
