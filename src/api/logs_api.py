"""
Logs API — exposes log buffer to the web UI via Eel.
"""
import eel
from utils.log_buffer import get_all, clear


def init_logs_api():
    """No per-instance state; reads directly from the log_buffer singleton."""
    pass


@eel.expose
def get_logs():
    """Return all buffered log entries (up to 2000)."""
    try:
        return {"success": True, "entries": get_all()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def clear_logs():
    """Clear all buffered log entries."""
    try:
        clear()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
