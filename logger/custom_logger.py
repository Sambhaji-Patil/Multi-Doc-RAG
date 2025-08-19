import os
import logging
import re
from datetime import datetime
import structlog
try:
    from config.config import CONSOLE_LOG_ENABLED
except Exception:
    CONSOLE_LOG_ENABLED = False


def _strip_emojis(text: str) -> str:
    """Remove common emoji / non-basic-multilingual-plane characters for a clean console output."""
    if not isinstance(text, str):
        return str(text)
    # Remove characters outside BMP which include most emoji glyphs
    try:
        emoji_re = re.compile(r"[\U00010000-\U0010FFFF]")
    except re.error:
        # Fallback for narrow builds
        emoji_re = re.compile(r"[\uD800-\uDBFF][\uDC00-\uDFFF]")
    return emoji_re.sub("", text)


class MultiLogger:
    """Writes detailed JSON logs to file (via structlog) and compact, emoji-free
    status lines to the console (via stdlib logging).
    """

    def __init__(self, json_logger, console_logger, console_enabled: bool):
        self._json_logger = json_logger
        self._console_logger = console_logger
        self._console_enabled = console_enabled

    def _minimal_msg(self, event: str, kwargs: dict) -> str:
        base = _strip_emojis(event)
        small_keys = [k for k in ("count", "chunks", "chars", "status", "filename", "doc_id") if k in kwargs]
        if not small_keys:
            return base
        parts = [f"{k}={kwargs[k]}" for k in small_keys]
        return f"{base} | {', '.join(parts)}"

    def info(self, event: str, **kwargs):
        self._json_logger.info(event, **kwargs)
        if self._console_enabled:
            try:
                self._console_logger.info(self._minimal_msg(event, kwargs))
            except Exception:
                pass

    def warning(self, event: str, **kwargs):
        self._json_logger.warning(event, **kwargs)
        if self._console_enabled:
            try:
                self._console_logger.warning(self._minimal_msg(event, kwargs))
            except Exception:
                pass

    def error(self, event: str, **kwargs):
        self._json_logger.error(event, **kwargs)
        if self._console_enabled:
            try:
                self._console_logger.error(self._minimal_msg(event, kwargs))
            except Exception:
                pass

    def exception(self, event: str, **kwargs):
        self._json_logger.exception(event, **kwargs)
        if self._console_enabled:
            try:
                self._console_logger.error(self._minimal_msg(event, kwargs), exc_info=True)
            except Exception:
                pass


class CustomLogger:
    # Class-level shared log file path to ensure a single file across modules
    _shared_log_file_path: str | None = None

    def __init__(self, log_dir="logs"):
        # Ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create a single shared, timestamped log file the first time
        if CustomLogger._shared_log_file_path is None:
            log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
            print(f"🟢 Logs will be saved at {log_file}")
            CustomLogger._shared_log_file_path = os.path.join(self.logs_dir, log_file)
        self.log_file_path = CustomLogger._shared_log_file_path

        # Configure stdlib logger for console (minimal, no emojis)
        self._console_logger = logging.getLogger("project_console")
        self._console_logger.setLevel(logging.INFO)
        self._console_logger.propagate = False
        # Avoid duplicate handlers on repeated instantiation
        if not self._console_logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter("%(message)s"))
            self._console_logger.addHandler(ch)

        # Toggle console output via config (with env fallback already handled in config)
        self._console_enabled = CONSOLE_LOG_ENABLED

    def get_logger(self, name=__file__):
        logger_name = os.path.basename(name)

        # Configure a file handler that will receive JSON lines rendered by structlog
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s"))  # Raw JSON lines from structlog

        # Configure root stdlib logging with the file handler only; console uses project_console
        root_logger = logging.getLogger()
        # Avoid adding duplicate file handlers on repeated calls
        if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == self.log_file_path for h in root_logger.handlers):
            root_logger.addHandler(file_handler)
            root_logger.setLevel(logging.INFO)

        # Configure structlog for JSON structured logging (for file)
        structlog.configure(
            processors=[
                # Ensure 'event' appears first in the JSON output
                structlog.processors.EventRenamer(to="event"),
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
                structlog.processors.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        json_logger = structlog.get_logger(logger_name)
        return MultiLogger(json_logger, self._console_logger, self._console_enabled)


