from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any

class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_URL: str
    BOT_ID: int
    ZAYAVKA_GROUP_ID: Optional[int] = None
    MANAGER_GROUP_ID: Optional[int] = None
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: Optional[str] = "aldb1"
    ADMINS_ID: int
    MEDIA_ROOT: str = "media"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

DB_CONFIG: Dict[str, Any] = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_NAME or 'aldb1'
}
