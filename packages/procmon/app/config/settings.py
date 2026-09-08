from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    API_SERVER: str = "http://localhost:8000"
    API_TIMEOUT_TOTAL: int = 20
    SPOOL_PATH: str = "/var/lib/jcode-watcher/spool/event-spool.db"
    SPOOL_BATCH_SIZE: int = 100
    SPOOL_RETRY_SECONDS: float = 2
    JCODE_ENVIRONMENT: Literal["dev", "prod"] = "prod"
    COURSE_ID_MAP_JSON: str = ""
    COURSE_ID_CACHE_SECONDS: int = 300
    KUBERNETES_API_URL: str = ""
    KUBERNETES_SERVICE_HOST: str = "kubernetes.default.svc"
    KUBERNETES_SERVICE_PORT_HTTPS: int = 443
    KUBERNETES_TOKEN_PATH: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    KUBERNETES_CA_PATH: str = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    # HW_MAX_COUNT: deprecated - 동적 워크스페이스에서는 사용하지 않음

    # 메트릭 설정
    METRICS_PORT: int = 3000

    # 로깅 설정
    LOG_FILE_PATH: str = "/opt/procmon/logs/procmon.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5


# 설정 객체 인스턴스화
settings = Settings()
