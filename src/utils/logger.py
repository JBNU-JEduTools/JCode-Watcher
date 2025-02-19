"""로깅 설정

애플리케이션의 로깅을 설정합니다.
"""
import logging
from ..config.settings import Config

# 기본 로거 설정
logging.basicConfig(
    level=Config.LOG_LEVEL_VALUE,
    format='%(asctime)s  %(levelname)-6s  [%(name)s]  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 외부 라이브러리 로깅 레벨 조정
logging.getLogger("watchdog").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 생성
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 또는 클래스명)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    return logging.getLogger(name) 