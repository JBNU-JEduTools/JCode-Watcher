from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """애플리케이션 설정"""

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    API_SERVER: str = "http://localhost:8000"

    # 메트릭 설정
    METRICS_PORT: int = 3000

    # 로깅 설정
    LOG_FILE_PATH: str = "/opt/procmon/logs/procmon.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 0 # 무제한


# 설정 객체 인스턴스화
settings = Settings()
