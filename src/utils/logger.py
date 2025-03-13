"""로깅 설정 모듈

이 모듈은 애플리케이션의 로깅 설정을 담당합니다.
"""
import logging
import sys
from ..config.settings import LOG_LEVEL

# 로그 포맷 설정
LOG_FORMAT = "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"

def setup_app_logger() -> None:
    """애플리케이션 로거 설정
    
    루트 로거는 WARNING 레벨로 설정하여 외부 라이브러리 로그를 제한하고,
    src 패키지의 로그만 LOG_LEVEL로 설정하여 상세 로깅을 활성화합니다.
    """
    # 1. 루트 로거 설정 (외부 라이브러리용)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # 외부 라이브러리는 기본적으로 WARNING 레벨
    
    # 2. 핸들러 설정
    # 기존 핸들러 제거
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)
    
    # 새 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(console_handler)
    
    # 3. 애플리케이션 로거 설정
    app_logger = logging.getLogger('src')
    app_logger.setLevel(LOG_LEVEL)
    app_logger.propagate = True  # 핸들러 중복을 방지하기 위해 루트 로거의 핸들러 사용

def get_logger(name: str) -> logging.Logger:
    """로거를 반환합니다.
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("메시지")  # 출력: 2024-03-13 14:00:00 - [src.app] - INFO - 메시지
    """
    # __main__으로 실행되는 경우나 src 디렉토리 내 모듈인 경우 처리
    if name == "__main__" or (not name.startswith('src') and 'src.' in name):
        name = name.replace('__main__', 'src.app')
    elif not name.startswith('src'):
        name = f"src.{name}"
    
    logger = logging.getLogger(name)
    return logger

# 초기 로거 설정
setup_app_logger()

"""
다른 모듈에서는 이렇게 사용:

from src.utils.logger import get_logger

logger = get_logger(__name__)  # 현재 모듈의 컨텍스트 정보가 포함된 로거 생성
"""