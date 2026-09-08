from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    WATCH_ROOT: Path = Path("/watcher/codes")
    SNAPSHOT_BASE: Path = Path("/watcher/snapshots")
    MAX_CAPTURABLE_FILE_SIZE: int = 64 * 1024  # 64KB - 저장할 수 있는 최대 파일 크기
    HW_MAX_COUNT: int = 15  # hw 디렉토리 최대 번호
    API_SERVER: str = "http://localhost:8080"  # API 서버 주소
    API_TIMEOUT_TOTAL: int = 20
    SPOOL_PATH: str = "/opt/filemon/logs/event-spool.db"
    SPOOL_BATCH_SIZE: int = 100
    SPOOL_RETRY_SECONDS: float = 2
    JCODE_ENVIRONMENT: Literal["dev", "prod"] = "prod"
    COURSE_ID_MAP_JSON: str = ""
    COURSE_ID_CACHE_SECONDS: int = 300
    FILE_WATCH_MODE: Literal["native", "polling"] = "native"
    FILE_POLL_INTERVAL_SECONDS: float = Field(default=5.0, gt=0)
    KUBERNETES_API_URL: str = ""
    KUBERNETES_SERVICE_HOST: str = "kubernetes.default.svc"
    KUBERNETES_SERVICE_PORT_HTTPS: int = 443
    KUBERNETES_TOKEN_PATH: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    KUBERNETES_CA_PATH: str = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

    # ThreadPool 설정
    THREAD_POOL_WORKERS: int = 8  # 파일 읽기용 스레드 풀 워커 수

    # Debounce 설정
    DEBOUNCE_WINDOW: float = 0.6  # modified 이벤트 600ms 대기
    DEBOUNCE_MAX_WAIT: float = 3  # 최대 대기 시간 3초

    # Logging 설정
    LOG_FILE_PATH: str = "/opt/filemon/logs/"
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5

    # Metrics 설정
    METRICS_PORT: int = 3000
    READINESS_PORT: int = 3001


# 애플리케이션 전체에서 사용할 단일 설정 인스턴스
settings = Settings()
