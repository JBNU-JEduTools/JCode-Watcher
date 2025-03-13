import asyncio
import os
import re
from src.utils.logger import get_logger
from watchdog.events import RegexMatchingEventHandler
from src.config.settings import (
    MAX_FILE_SIZE,
    SOURCE_PATTERNS,
    IGNORE_PATTERNS
)

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

class SourceCodeHandler(RegexMatchingEventHandler):
    def __init__(self, event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__(
            regexes=SOURCE_PATTERNS,
            ignore_regexes=IGNORE_PATTERNS,
            ignore_directories=True,
            case_sensitive=False
        )
        self.event_queue = event_queue
        self.loop = loop

    def on_modified(self, event):
        try:
            if os.path.getsize(event.src_path) > MAX_FILE_SIZE:
                return
            
            asyncio.run_coroutine_threadsafe(
                self.event_queue.put({
                    "event_type": "modified",
                    "path": event.src_path
                }), 
                self.loop
            )
        except OSError:
            return

    def on_deleted(self, event):
        asyncio.run_coroutine_threadsafe(
            self.event_queue.put({
                "event_type": "deleted",
                "path": event.src_path
            }), 
            self.loop
        )
        
    # 정규표현식 디버깅을 위한 테스트 메서드 추가
    @classmethod
    def test_path(cls, path: str) -> bool:
        """주어진 경로가 허용된 패턴과 일치하는지 테스트합니다."""
        # 디버깅을 위한 로깅 추가
        logger.debug(f"Testing path: {path}")
        
        # 먼저 무시 패턴과 매칭되는지 확인
        for pattern in cls.IGNORE_PATTERNS:
            if re.match(pattern, path):
                logger.debug(f"Path matched ignore pattern: {pattern}")
                return False
        
        # 허용 패턴과 매칭되는지 확인
        for pattern in cls.SOURCE_PATTERNS:
            if re.match(pattern, path):
                logger.debug(f"Path matched source pattern: {pattern}")
                return True
        
        logger.debug("Path did not match any patterns")
        return False