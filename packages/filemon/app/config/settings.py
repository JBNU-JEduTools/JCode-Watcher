from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    WATCH_ROOT: Path = Path('/watcher/codes')
    SNAPSHOT_BASE: Path = Path('/watcher/snapshots')
    MAX_CAPTURABLE_FILE_SIZE: int = 64 * 1024  # 64KB - 저장할 수 있는 최대 파일 크기
    API_SERVER: str = "http://localhost:8080"  # API 서버 주소
    API_TIMEOUT_TOTAL: int = 20
    
    # Debounce 설정
    DEBOUNCE_WINDOW: float = 1  # modified 이벤트 1000ms 대기
    DEBOUNCE_MAX_WAIT: float = 4  # 최대 대기 시간 4초


# 애플리케이션 전체에서 사용할 단일 설정 인스턴스
settings = Settings()
