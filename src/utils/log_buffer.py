"""
Thread-safe ring buffer for application log entries.

Stores up to 2000 entries (oldest auto-dropped by deque).
Pushes new entries to the browser in real-time via eel.receive_log().
Also writes to a rotating file log/app.log for offline debugging.
"""
import threading
import logging
import logging.handlers
from collections import deque
from datetime import datetime
from pathlib import Path

_lock = threading.Lock()
_buffer = deque(maxlen=2000)
_eel = None       # Set via init_log_buffer() after eel.init()
_file_logger = None  # Python logger writing to log/app.log


# ── File logger setup ─────────────────────────────────────────────────────────

def init_file_logger(log_dir: str = "log"):
    """
    Set up rotating file logger.  Called early in main.py (before eel.init).
    Creates log/<date>_app.log, max 5 MB per file, 3 backups kept.
    """
    global _file_logger
    if _file_logger is not None:
        return  # Already initialized

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_path / f"{today}_app.log"

    logger = logging.getLogger("EDEvent2Led")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Don't bubble up to root logger

    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    _file_logger = logger

    _file_logger.info(f"=== ED:Event2Led log started  ({log_file.name}) ===")


def init_log_buffer(eel_module):
    """Register the eel module so new entries can be pushed to the browser."""
    global _eel
    _eel = eel_module
    if _file_logger is None:
        init_file_logger()  # Fallback: init file logger if not done earlier


# ── Core log entry ────────────────────────────────────────────────────────────

def log_entry(level: str, category: str, message: str):
    """
    Append one log entry, write to file, and push it to the browser.

    Args:
        level:    'info' | 'warning' | 'error'
        category: 'EVENT' | 'RENDER' | 'OPENRGB' | 'SYSTEM' | 'LED' | 'WARNING' | 'ERROR'
        message:  Human-readable description (ASCII-safe for Windows console)
    """
    now = datetime.now()
    entry = {
        "ts": now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}",
        "level": level,
        "category": category,
        "message": message,
    }
    with _lock:
        _buffer.append(entry)

    # Write to file logger
    if _file_logger is not None:
        file_msg = f"[{category:8s}]  {message}"
        if level == "error":
            _file_logger.error(file_msg)
        elif level == "warning":
            _file_logger.warning(file_msg)
        else:
            _file_logger.info(file_msg)

    # Real-time push — fire-and-forget; silently ignored when browser is not connected
    if _eel is not None:
        try:
            _eel.receive_log(entry)
        except Exception:
            pass


def log_led(device_name: str, action: str, detail: str = ""):
    """
    Dedicated LED-state log entry.  Writes to file with 'LED' category.
    Use this for detailed hardware state changes (color set, fade start, etc.)

    Args:
        device_name: Short device identifier
        action:      What happened ('fade_start', 'post_behavior', 'set_color', etc.)
        detail:      Extra info (color value, LED count, step index, etc.)
    """
    msg = f"{device_name}  [{action}]"
    if detail:
        msg += f"  {detail}"
    log_entry("info", "LED", msg)


# ── Buffer read/clear ─────────────────────────────────────────────────────────

def get_all() -> list:
    """Return a snapshot of all buffered entries (oldest -> newest)."""
    with _lock:
        return list(_buffer)


def clear():
    """Discard all buffered entries."""
    with _lock:
        _buffer.clear()
