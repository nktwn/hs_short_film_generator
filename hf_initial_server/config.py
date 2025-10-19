# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DEFAULT_DURATION_S: int = 10
    DEFAULT_ASPECT_RATIO: str = "16:9"
    DEFAULT_MODEL: str = "minimax-t2v"      
    DEFAULT_RESOLUTION: str = "768"
    DEFAULT_LANGUAGE: str = "en"
    PROVIDER: str = "higgsfield"
    HIGGSFIELD_BASE_URL: str = "https://platform.higgsfield.ai"
    HIGGSFIELD_API_KEY: str
    HIGGSFIELD_API_SECRET: str
    REQUEST_TIMEOUT: float = 60.0
    MAX_SYNC_WAIT_SEC: int = 20
    CORS_ALLOW_ORIGINS: str = "*"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
