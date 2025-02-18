"""로깅 설정 모듈"""
import logging
from ..config.settings import Config

def setup_logger() -> None:
    """애플리케이션 로거 설정
    
    중복 로깅을 방지하고 일관된 포맷을 적용합니다.
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(Config.LOG_LEVEL_VALUE)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # 새로운 핸들러 추가
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt='%(asctime)s  %(levelname)-6s  [%(name)s]  %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    root_logger.addHandler(handler)
    
    # 외부 라이브러리 로깅 레벨 설정
    for logger_name, level in Config.LIBRARY_LOG_LEVELS.items():
        logging.getLogger(logger_name).setLevel(level)
        
def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 생성
    
    Args:
        name: 로거 이름 (일반적으로 __name__ 또는 클래스명)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    return logging.getLogger(name) 