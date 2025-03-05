from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

DIR = Path(__file__).resolve().parent.parent   # 현재 파일의 상위 디렉터리
ENV_PATH = DIR / ".env"

class Settings(BaseSettings):
    DB_URL: str
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH)
    )
        
settings = Settings()