from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    BASE_PATH: Path = Path('/watcher/codes')
    SNAPSHOT_BASE: Path = Path('/watcher/snapshots')


# 애플리케이션 전체에서 사용할 단일 설정 인스턴스
settings = Settings()
