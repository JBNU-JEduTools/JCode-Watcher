from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DIR = Path(__file__).resolve().parent.parent  # 현재 파일의 상위 디렉터리
ENV_PATH = DIR / ".env"


class Settings(BaseSettings):
    DB_URL: str
    AUTO_CREATE_SCHEMA: bool = False
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=5, ge=0, le=50)
    DB_POOL_TIMEOUT_SECONDS: int = Field(default=30, ge=1, le=300)

    model_config = SettingsConfigDict(env_file=str(ENV_PATH))


settings = Settings()
