"""
Update check: is a newer release published on GitHub?

At startup a background thread asks the GitHub API for the latest release of
the public repository (one HTTPS request, no personal data: only the app name
and version in the User-Agent). The web UI polls get_update_status() and shows
a toast with a link to the release page.

The check can be turned off in Settings ("check_updates": false); a version the
user dismissed is not announced again ("update_dismissed_version").
"""
from __future__ import annotations

import json
import re
import threading
import urllib.request

import eel

PUBLIC_REPO = "leandor70/EDEvent2Led"
LATEST_URL = f"https://api.github.com/repos/{PUBLIC_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{PUBLIC_REPO}/releases"
TIMEOUT_S = 6.0

_settings = None
_lock = threading.Lock()
# state: "disabled" | "pending" | "none" | "available" | "error"
_status: dict = {"state": "pending"}

_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    """'v1.3.0', '1.3.0', 'v1.3.0-2-gabc-dirty' -> (1, 3, 0). None if no version."""
    m = _VERSION_RE.search(text or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def evaluate(current: str | None, release: dict, dismissed: str | None = None) -> dict:
    """Compare the running version with a GitHub 'latest release' payload."""
    latest_tag = release.get("tag_name") or ""
    cur, new = parse_version(current), parse_version(latest_tag)
    result = {
        "current": current or "",
        "latest": latest_tag,
        "url": release.get("html_url") or RELEASES_PAGE,
        "name": release.get("name") or latest_tag,
    }
    if cur is None or new is None or release.get("draft") or release.get("prerelease"):
        return {**result, "state": "none"}
    if new <= cur:
        return {**result, "state": "none"}
    if dismissed and parse_version(dismissed) == new:
        return {**result, "state": "none", "dismissed": True}
    return {**result, "state": "available"}


def _fetch_latest(current: str) -> dict:
    req = urllib.request.Request(LATEST_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"ED-Event2Led/{current or 'unknown'}",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _current_version() -> str:
    from api.settings_api import _get_cached_git_info
    return _get_cached_git_info().get("version", "")


def _run_check(fetch=_fetch_latest, current_version=_current_version) -> None:
    global _status
    try:
        current = current_version()
        release = fetch(current)
        dismissed = _settings.settings.get("update_dismissed_version") if _settings else None
        status = evaluate(current, release, dismissed)
    except Exception as e:                       # offline, rate limit, GitHub down: stay quiet
        print(f"[Update] Check failed: {type(e).__name__}: {e}")
        status = {"state": "error"}
    with _lock:
        _status = status
    if status["state"] == "available":
        print(f"[Update] New version available: {status['latest']} (running {status['current']})")


def check_enabled() -> bool:
    return bool(_settings.settings.get("check_updates", True)) if _settings else False


def start_update_check() -> None:
    """Run the check once, in the background. No-op when disabled."""
    global _status
    if not check_enabled():
        with _lock:
            _status = {"state": "disabled"}
        return
    with _lock:
        _status = {"state": "pending"}
    threading.Thread(target=_run_check, name="update-check", daemon=True).start()


def init_update_api(settings) -> None:
    global _settings
    _settings = settings
    start_update_check()


@eel.expose
def get_update_status():
    """{'state': 'disabled'|'pending'|'none'|'available'|'error', 'current', 'latest', 'url', 'name'}"""
    with _lock:
        return dict(_status)


@eel.expose
def dismiss_update(version: str):
    """Do not announce this version again."""
    global _status
    if _settings is None:
        return {"success": False}
    _settings.settings["update_dismissed_version"] = str(version)
    _settings._save_settings()
    with _lock:
        if _status.get("latest") == version:
            _status = {**_status, "state": "none", "dismissed": True}
    return {"success": True}


@eel.expose
def get_check_updates():
    return check_enabled()


@eel.expose
def set_check_updates(enabled: bool):
    """Turn the startup check on or off. Turning it on checks right away."""
    global _status
    if _settings is None:
        return {"success": False}
    _settings.settings["check_updates"] = bool(enabled)
    _settings._save_settings()
    if enabled:
        start_update_check()
    else:
        with _lock:
            _status = {"state": "disabled"}
    return {"success": True}
