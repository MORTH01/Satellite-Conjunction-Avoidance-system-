from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg:///conjunction_db"
    DATABASE_URL_SYNC: str = "postgresql:///conjunction_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SPACETRACK_USER: str = ""
    SPACETRACK_PASS: str = ""
    SPACETRACK_BASE_URL: str = "https://www.space-track.org"
    SECRET_KEY: str = "dev-secret-key"
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    PC_ALERT_THRESHOLD: float = 1e-4
    SCREEN_MISS_DISTANCE_KM: float = 10.0
    HARD_BODY_RADIUS_M: float = 10.0
    SCREEN_DAYS: int = 7
    SCREEN_TIMESTEP_S: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()