"""설정 관리 모듈"""
import os
import logging

class Config:
    """전역 설정 클래스"""
    
    # 로깅 설정
    LOG_LEVEL = os.getenv("WATCHER_LOG_LEVEL", "INFO").upper()
    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    LOG_LEVEL_VALUE = LOG_LEVELS.get(LOG_LEVEL, logging.INFO)
    
    # 외부 라이브러리 로깅 레벨
    LIBRARY_LOG_LEVELS = {
        "watchdog": logging.WARNING,
        "asyncio": logging.WARNING,
        "aiohttp": logging.WARNING
    }
    
    # API 서버 설정
    API_URL = os.getenv("WATCHER_API_URL", "http://localhost:5000")
    API_TIMEOUT = float(os.getenv("WATCHER_API_TIMEOUT", "5.0"))
    
    # 기본 경로 설정
    BASE_PATH = os.getenv("WATCHER_BASE_PATH", "/watcher/codes")
    SNAPSHOT_PATH = os.getenv("WATCHER_SNAPSHOT_PATH", "/watcher/snapshots")
    
    # 감시 패턴 설정
    WATCH_PATTERN = os.getenv("WATCHER_WATCH_PATTERN", "*-*-*")  # 예: ai-1-202012180
    HOMEWORK_PATTERN = os.getenv("WATCHER_HOMEWORK_PATTERN", "hw*")  # 예: hw1, hw2
    
    # 이벤트 큐 설정
    QUEUE_SIZE = int(os.getenv("WATCHER_QUEUE_SIZE", "1000"))
    
    # 파일 필터 설정
    ALLOWED_EXTENSIONS = {
        ext.strip()
        for ext in os.getenv(
            "WATCHER_ALLOWED_EXTENSIONS",
            ".c,.cpp,.py,.java"
        ).split(",")
    }
    
    # 기본 무시 패턴
    DEFAULT_IGNORE_PATTERNS = {
        "*/__pycache__/*",
        "*/.*",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.dylib",
        "*.dll"
    }
    
    # 사용자 정의 무시 패턴
    USER_IGNORE_PATTERNS = {
        pattern.strip()
        for pattern in os.getenv("WATCHER_IGNORE_PATTERNS", "").split(",")
        if pattern.strip()
    }
    
    # 전체 무시 패턴
    IGNORE_PATTERNS = DEFAULT_IGNORE_PATTERNS | USER_IGNORE_PATTERNS 