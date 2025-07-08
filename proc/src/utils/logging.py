import logging
import sys
import contextvars
from typing import Optional

# Context variables
current_pid = contextvars.ContextVar('pid', default=None)
current_hostname = contextvars.ContextVar('hostname', default=None)  # hostname 추가

class ProcessContextFilter(logging.Filter):  # 이름 변경 (더 일반적인 이름으로)
    """PID와 hostname 정보를 로그 레코드에 추가하는 필터"""
    
    def filter(self, record):
        # PID 설정
        pid = current_pid.get()
        record.pid = pid if pid else "---"  # PID: 접두어 제거
        
        # Hostname 설정
        hostname = current_hostname.get()
        record.hostname = hostname if hostname else "---"
        return True

def get_logger(name: str) -> logging.Logger:
    """컨텍스트 정보가 포함된 로거를 반환합니다."""
    logger = logging.getLogger(name)
    logger.addFilter(ProcessContextFilter())
    return logger

def set_pid(pid: Optional[int]):
    """현재 컨텍스트의 PID를 설정합니다."""
    current_pid.set(pid)

def set_hostname(hostname: Optional[str]):  # hostname setter 추가
    """현재 컨텍스트의 hostname을 설정합니다."""
    current_hostname.set(hostname)

def setup_logging(level: int = logging.INFO):
    """기본 로깅 설정
    
    Args:
        level: 로깅 레벨 (기본값: logging.INFO)
    """
    # 루트 로거 설정
    root = logging.getLogger()
    root.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root.handlers:
        root.removeHandler(handler)
    
    # 새 핸들러 생성 및 설정
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ProcessContextFilter())
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(hostname)s - %(pid)s - %(name)s - %(message)s')
    )
    
    # 핸들러 추가
    root.addHandler(handler)
    
    # 설정 완료 로그
    logger = get_logger(__name__)
    logger.debug(f"[설정] 로깅 설정 완료 (레벨: {logging.getLevelName(level)})") 