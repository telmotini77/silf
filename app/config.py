from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import json

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"
    TIMEZONE: str = "America/Guayaquil"

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    TELEGRAM_GROUP_ID: Optional[str] = None
    ADMIN_TOKEN: Optional[str] = None

    # La única fuente de correo es Carbonio IMAP.
    ACTIVE_SOURCES: List[str] = ["carbonio"]
    
    # Ingestion Filters
    ALLOWED_SENDERS: str = "[]" # JSON list
    SUBJECT_KEYWORDS: str = "[]" # JSON list

    # Carbonio IMAP (cuenta dedicada de solo lectura por defecto)
    CARBONIO_IMAP_SERVER: Optional[str] = None
    CARBONIO_IMAP_PORT: int = 993
    CARBONIO_EMAIL: Optional[str] = None
    CARBONIO_PASSWORD: Optional[str] = None
    CARBONIO_FOLDER: str = "INBOX"
    CARBONIO_CA_FILE: Optional[str] = None
    CARBONIO_POLL_SECONDS: int = 30
    BACKFILL_DAYS: int = 0
    MARK_AS_SEEN: bool = False
    MOVE_TO: Optional[str] = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    @property
    def allowed_senders_list(self) -> List[str]:
        try:
            return json.loads(self.ALLOWED_SENDERS)
        except (TypeError, json.JSONDecodeError):
            return []
            
    @property
    def subject_keywords_list(self) -> List[str]:
        try:
            return json.loads(self.SUBJECT_KEYWORDS)
        except (TypeError, json.JSONDecodeError):
            return []

    def check_source(self, source: str) -> None:
        if source == "carbonio":
            if not all([self.CARBONIO_IMAP_SERVER, self.CARBONIO_EMAIL, self.CARBONIO_PASSWORD]):
                raise ValueError("Carbonio IMAP configuration is incomplete")
        else:
            raise ValueError(f"Unknown source: {source}")

settings = Settings()
