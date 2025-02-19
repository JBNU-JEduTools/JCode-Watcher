"""설정 관리

애플리케이션의 설정을 관리합니다.
"""
import os
import logging

class Config:
    """전역 설정"""
    
    # 로깅 설정
    LOG_LEVEL = os.getenv("WATCHER_LOG_LEVEL", "INFO").upper()
    LOG_LEVEL_VALUE = getattr(logging, LOG_LEVEL, logging.INFO)
    
    # API 서버 설정
    API_URL = os.getenv("WATCHER_API_URL", "http://localhost:3000")
    API_TIMEOUT = float(os.getenv("WATCHER_API_TIMEOUT", "5.0"))
    
    # 기본 경로 설정
    BASE_PATH = os.getenv("WATCHER_BASE_PATH", "/watcher/codes")
    SNAPSHOT_PATH = os.getenv("WATCHER_SNAPSHOT_PATH", "/watcher/snapshots")
    
    # 감시 패턴 설정
    WATCH_PATTERN = os.getenv("WATCHER_WATCH_PATTERN", "*-*-*")
    HOMEWORK_PATTERN = os.getenv("WATCHER_HOMEWORK_PATTERN", "hw*")
    
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
    
    # 무시 패턴
    IGNORE_PATTERNS = {
        "*/__pycache__/*",
        "*/.*",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.dylib",
        "*.dll",
        *[p.strip() for p in os.getenv("WATCHER_IGNORE_PATTERNS", "").split(",") if p.strip()]
    } 