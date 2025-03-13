"""로깅 설정 모듈

이 모듈은 애플리케이션의 로깅 설정을 담당합니다.
"""
import logging
import sys
from ..config.settings import LOG_LEVEL

# 로그 포맷 설정
LOG_FORMAT = "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"

def setup_app_logger() -> logging.Logger:
    """애플리케이션 로거 설정"""
    # 외부 라이브러리 로그 레벨 설정 (기본값: WARNING)
    logging.getLogger().setLevel(logging.WARNING)
    
    # 애플리케이션 로거 설정
    app_logger = logging.getLogger('src')
    app_logger.setLevel(LOG_LEVEL)
    
    # 기존 핸들러 제거
    for handler in app_logger.handlers:
        app_logger.removeHandler(handler)
    
    # 로그 레벨과 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    app_logger.addHandler(console_handler)
    
    return app_logger

def get_logger(name: str) -> logging.Logger:
    """컨텍스트 정보가 포함된 로거를 반환합니다.
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("메시지")  # 출력: 2024-03-13 14:00:00 - [app.core.snapshot] - INFO - 메시지
    """
    return logging.getLogger(name)

# 기본 로거 설정 초기화
setup_app_logger()

"""
다른 모듈에서는 이렇게 사용:

from src.utils.logger import get_logger

logger = get_logger(__name__)  # 현재 모듈의 컨텍스트 정보가 포함된 로거 생성
"""