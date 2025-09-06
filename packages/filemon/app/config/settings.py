from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    WATCH_ROOT: Path = Path('/watcher/codes')
    SNAPSHOT_BASE: Path = Path('/watcher/snapshots')
    MAX_CAPTURABLE_FILE_SIZE: int = 64 * 1024  # 64KB - 저장할 수 있는 최대 파일 크기
    API_SERVER: str = "http://localhost:8080"  # API 서버 주소
    API_TIMEOUT_TOTAL: int = 20
    
    # ThreadPool 설정
    THREAD_POOL_WORKERS: int = 8  # 파일 읽기용 스레드 풀 워커 수
    
    # Debounce 설정
    DEBOUNCE_WINDOW: float = 0.6  # modified 이벤트 600ms 대기
    DEBOUNCE_MAX_WAIT: float = 3  # 최대 대기 시간 3초
    
    # Logging 설정
    LOG_FILE_PATH: str = "/opt/filemon/logs/"
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 0

    # Metrics 설정
    METRICS_PORT: int = 3000


# 애플리케이션 전체에서 사용할 단일 설정 인스턴스
settings = Settings()
