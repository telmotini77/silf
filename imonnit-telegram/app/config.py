from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional, List
import json
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "America/Guayaquil"

    # Carbonio IMAP
    CARBONIO_HOST: str
    CARBONIO_PORT: int = 993
    CARBONIO_USER: str
    CARBONIO_PASSWORD: str
    CARBONIO_FOLDER: str = "INBOX"
    CARBONIO_CA_FILE: Optional[str] = None
    
    IDLE_RENEW_MINUTES: int = 25
    BACKFILL_DAYS: int = 0
    MARK_AS_SEEN: bool = False
    MOVE_TO: Optional[str] = None
    CACHE_RAW: bool = False

    # Filtros
    ALLOWED_SENDERS: str = "[]"
    SUBJECT_KEYWORDS: str = "[]"

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    TELEGRAM_MODE: Literal["equivalent", "exact", "both"] = "both"

    # Base de Datos y App
    DATABASE_URL: str
    ADMIN_TOKEN: str
    MAX_ATTEMPTS: int = 8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_senders_list(self) -> List[str]:
        try: return json.loads(self.ALLOWED_SENDERS)
        except: return []

    @property
    def subject_keywords_list(self) -> List[str]:
        try: return json.loads(self.SUBJECT_KEYWORDS)
        except: return []

    def validate_at_startup(self):
        missing = []
        if not self.CARBONIO_HOST: missing.append("CARBONIO_HOST")
        if not self.CARBONIO_USER: missing.append("CARBONIO_USER")
        if not self.CARBONIO_PASSWORD: missing.append("CARBONIO_PASSWORD")
        if not self.TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        if not self.TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
        if not self.DATABASE_URL: missing.append("DATABASE_URL")
        
        if self.CARBONIO_CA_FILE and not os.path.exists(self.CARBONIO_CA_FILE):
            raise ValueError(f"CARBONIO_CA_FILE not found: {self.CARBONIO_CA_FILE}")
            
        if missing:
            raise ValueError(f"Variables requeridas faltantes: {', '.join(missing)}")

settings = Settings()
