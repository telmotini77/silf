import logging
import sys
import json

def setup_logging():
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "time": self.formatTime(record, self.datefmt)
            }
            if record.exc_info:
                log_record["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    root_logger = logging.getLogger()
    
    from app.config import settings
    lvl = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(lvl)
    root_logger.addHandler(handler)
    
    # Silenciar httpx y httpcore
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
