"""
Settings API - Eel exposed functions for settings management.
"""

import eel
import sys
import time
from pathlib import Path

# Global references (Eel needs module-level functions)
_settings = None
_visual_library = None  # Kept for lazy hardware init on first successful connection

# Cooldown for failed OpenRGB probe — avoids hammering the socket on every
# hardware API call when OpenRGB is down.
_PROBE_COOLDOWN_S = 5.0
_last_probe_failed = 0.0

# Cached ping for connection status polling — avoids TCP probe on every 1s poll.
# Cache is invalidated immediately when renderer detects a disconnect.
_ping_cache_result: bool = True
_ping_cache_time: float = 0.0
_PING_CACHE_TTL_S: float = 5.0  # Re-probe at most every 5 seconds


def _cached_ping(host: str, port: int, client=None) -> bool:
    """Ping with cache: re-probes at most every _PING_CACHE_TTL_S seconds.

    With the app's client, the probe is a request on ITS connection: it also
    catches a dead socket after OpenRGB was restarted (a fresh TCP probe would
    succeed there), and it does not open a new connection to OpenRGB each time.
    A client that already knows it is disconnected is reported at once, with no I/O.
    """
    global _ping_cache_result, _ping_cache_time
    if client is not None and not getattr(client, "connected", True):
        return False
    if time.time() - _ping_cache_time >= _PING_CACHE_TTL_S:
        if client is not None and hasattr(client, "ping"):
            try:
                client.ping(timeout=1.0)
                _ping_cache_result = True
            except Exception:
                _ping_cache_result = False
        else:
            _ping_cache_result = _ping_openrgb(host, port)
        _ping_cache_time = time.time()
    return _ping_cache_result


def invalidate_ping_cache():
    """Force next status poll to re-probe immediately (called on renderer disconnect)."""
    global _ping_cache_time
    _ping_cache_time = 0.0


# Async reconnection state (Tier 2)
_reconnect_in_progress = False
_reconnect_result = None


def _ping_openrgb(host: str, port: int) -> bool:
    """Lightweight TCP reachability check (1-second timeout)."""
    import socket as _sock

    probe = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
    probe.settimeout(1)
    reachable = probe.connect_ex((host, port)) == 0
    probe.close()
    return reachable


def init_settings_api(settings, visual_library=None):
    """Initialize settings API with settings instance.

    Args:
        settings: Settings instance
        visual_library: VisualEffectLibrary instance (optional).
            If provided, a successful test_openrgb_connection() call will also
            fully initialize effects/devices/keyboard API modules with a live manager.
    """
    global _settings, _visual_library
    _settings = settings
    _visual_library = visual_library
    print("[OK] Settings API initialized")


@eel.expose
def get_settings():
    """Get all current settings."""
    if not _settings:
        return {"error": "Settings not initialized"}

    result = {
        "language": _settings.settings.get("language", "en"),
        "theme": _settings.settings.get("theme", "dark"),
        "openrgb_host": _settings.get_openrgb_host(),
        "openrgb_port": _settings.get_openrgb_port(),
        "journal_directory": _settings.get_journal_directory()
        or _settings.get_default_journal_directory(),
    }
    return result


@eel.expose
def save_settings(settings_data):
    """Save settings from frontend."""
    if not _settings:
        return {"success": False, "message": "Settings not initialized"}

    try:
        # Language
        _settings.settings["language"] = settings_data["language"]

        # Theme
        _settings.settings["theme"] = settings_data["theme"]

        # OpenRGB
        _settings.set_openrgb_connection(
            settings_data["openrgb_host"], settings_data["openrgb_port"]
        )

        # Journal directory
        _settings.set_journal_directory(settings_data["journal_directory"])

        # Save to file
        _settings._save_settings()

        print("[OK] Settings saved successfully")
        return {"success": True, "message": "Settings saved successfully!"}
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")
        return {"success": False, "message": f"Error saving settings: {str(e)}"}


@eel.expose
def get_openrgb_status():
    """Check if OpenRGB server is reachable via lightweight socket ping.

    Does NOT create an OpenRGBClient, does NOT reinitialize the hardware stack.
    Safe to call on every page load.

    Returns:
        dict: {
            'reachable': bool,
            'host': str,
            'port': int
        }
    """
    if not _settings:
        return {"reachable": False, "host": "127.0.0.1", "port": 6742}

    host = _settings.get_openrgb_host()
    port = _settings.get_openrgb_port()
    reachable = _ping_openrgb(host, port)
    return {"reachable": reachable, "host": host, "port": port}


@eel.expose
def test_openrgb_connection():
    """Test OpenRGB connection.

    If a visual_library was provided at init time, a successful connection also
    fully initializes effects/devices/keyboard API modules so that hardware
    testing works immediately without a server restart.
    """
    if not _settings:
        return {"connected": False, "message": "Settings not initialized"}

    try:
        from utils.openrgb_client import OpenRGBClient

        client = OpenRGBClient(
            _settings.get_openrgb_host(), _settings.get_openrgb_port()
        )
        device_count = len(client.devices)
        print(f"[OK] OpenRGB connected: {device_count} device(s)")

        # Fully initialize hardware stack so effects/devices APIs become usable.
        if _visual_library:
            _initialize_hardware(client)

        return {
            "connected": True,
            "device_count": device_count,
            "message": f"Connected! Found {device_count} device(s).",
        }
    except Exception as e:
        print(f"[ERROR] OpenRGB connection failed: {e}")
        return {
            "connected": False,
            "device_count": 0,
            "message": f"Connection failed: {str(e)}",
        }


@eel.expose
def get_openrgb_connection_status():
    """
    Get current OpenRGB connection status (for frontend polling).

    Uses a cached ping (TTL: 5s) to avoid hammering OpenRGB with a TCP probe
    on every poll cycle. The cache is invalidated immediately when the renderer
    detects a disconnect, so Tier 1/2/3 reaction time is not affected.

    Returns:
        dict: {
            'connected': bool,
            'device_count': int,
            'reconnecting': bool  # True if background reconnection in progress
        }
    """
    import api.keyboard_api as _kbd

    if not _settings:
        return {"connected": False, "device_count": 0, "reconnecting": False}

    # If no manager, definitely disconnected (reconnect logic runs separately)
    if _kbd._manager is None:
        return {
            "connected": False,
            "device_count": 0,
            "reconnecting": _reconnect_in_progress,
        }

    host = _settings.get_openrgb_host()
    port = _settings.get_openrgb_port()

    if _cached_ping(host, port, getattr(_kbd._manager, "client", None)):
        return {
            "connected": True,
            "device_count": len(_kbd._manager.devices),
            "reconnecting": False,
        }
    else:
        return {
            "connected": False,
            "device_count": 0,
            "reconnecting": _reconnect_in_progress,
        }


@eel.expose
def invalidate_openrgb_connection():
    """
    Invalidate current OpenRGB connection state (called when polling detects disconnection).
    This ensures next API call will trigger reconnection attempt.
    """
    import api.keyboard_api as _kbd
    import api.effects_api as _fx
    import api.devices_api as _dev

    print("[INFO] Invalidating OpenRGB connection state (detected by polling)")

    # Reset all module managers to None
    _kbd._manager = None
    _fx._manager = None
    _fx._renderer = None
    _dev._manager = None

    return {"success": True}


@eel.expose
def trigger_auto_reconnect():
    """
    Trigger automatic reconnection attempt (called by polling when disconnect detected).
    Starts background thread that retries connection for up to 10 seconds.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    print("[INFO] Auto-reconnection triggered by polling")

    # Call try_ensure_openrgb with notify_ui=False since polling already showed toast
    try_ensure_openrgb(notify_ui=False)

    return {"success": True, "message": "Auto-reconnection attempt started"}


def try_ensure_openrgb(notify_ui: bool = True) -> bool:
    """
    Shared lazy-connection helper with async reconnection (Tier 2).

    Args:
        notify_ui: Send toast notification during reconnection

    Returns:
        True if OpenRGB connected, False otherwise

    Usage in any api/*.py::

        from api.settings_api import try_ensure_openrgb

        @eel.expose
        def my_hardware_function(...):
            if not try_ensure_openrgb():
                return {'success': False, 'error': 'OpenRGB not reachable'}
            ...
    """
    import api.keyboard_api as _kbd

    # Quick check: already connected?
    if _kbd._manager is not None:
        return True

    if not _settings:
        return False

    global _last_probe_failed, _reconnect_in_progress, _reconnect_result

    # Check cooldown (non-blocking)
    now = time.monotonic()
    if now - _last_probe_failed < _PROBE_COOLDOWN_S:
        if _reconnect_in_progress:
            return False
        return False

    if _reconnect_in_progress:
        return False

    # Start async reconnection
    _reconnect_in_progress = True

    def _async_reconnect():
        global _last_probe_failed, _reconnect_in_progress, _reconnect_result

        try:
            host = _settings.get_openrgb_host()
            port = _settings.get_openrgb_port()

            # Send toast notification
            if notify_ui:
                try:
                    import eel

                    eel.show_reconnect_toast()
                except:
                    pass

            # Retry polling loop: try up to 10 times with 1s interval (10s total)
            max_retries = 10
            retry_interval = 1.0  # seconds

            print(
                f"[INFO] Background reconnection starting (max {max_retries} retries, {retry_interval}s interval)"
            )

            for attempt in range(1, max_retries + 1):
                print(f"[INFO] Reconnect attempt {attempt}/{max_retries}...")

                if _ping_openrgb(host, port):
                    print(f"[OK] Ping successful on attempt {attempt}")
                    break

                if attempt < max_retries:
                    time.sleep(retry_interval)
            else:
                # All retries failed — confirm with 3 additional pings (2s apart)
                # before escalating to Tier 3, to avoid false positives from
                # transient network glitches.
                print(
                    f"[WARN] All {max_retries} reconnection attempts failed — confirming..."
                )
                confirmed_down = True
                for confirm_attempt in range(1, 4):
                    time.sleep(2.0)
                    if _ping_openrgb(host, port):
                        print(
                            f"[INFO] Confirmation ping {confirm_attempt}/3 succeeded — server is back, aborting Tier 3"
                        )
                        confirmed_down = False
                        break
                    print(f"[INFO] Confirmation ping {confirm_attempt}/3 failed")

                _last_probe_failed = time.monotonic()
                _reconnect_result = False

                if confirmed_down:
                    print(
                        f"[WARN] Server confirmed unreachable — triggering Tier 3 modal"
                    )
                    try:
                        from api.effects_api import set_connection_lost_flag

                        set_connection_lost_flag(True, [])
                    except Exception:
                        pass
                return

            # Connect
            print(f"[INFO] Ping succeeded, connecting to OpenRGB at {host}:{port}...")
            from utils.openrgb_client import OpenRGBClient

            client = OpenRGBClient(host, port)
            _initialize_hardware(client)

            n = _kbd._manager and len(_kbd._manager.devices)
            print(f"[OK] Auto-reconnected - {n or 0} devices")

            _reconnect_result = True

            # NOTE: Frontend will detect reconnection via polling get_openrgb_connection_status()
            # and show success toast + remove blue toast automatically.
            # Direct Eel calls from background thread don't work due to WebSocket threading limitations.

        except Exception as exc:
            print(f"[WARN] Auto-reconnect failed: {exc}")
            _last_probe_failed = time.monotonic()
            _reconnect_result = False

        finally:
            _reconnect_in_progress = False

    # Launch background thread
    import threading

    threading.Thread(target=_async_reconnect, daemon=True).start()

    return False


def _initialize_hardware(client):
    """Create UnifiedEffectManager and re-init all hardware-dependent API modules.

    Called after a successful OpenRGB connection (either at startup or via
    test_openrgb_connection).  Safe to call multiple times — each call replaces
    the previous manager with a fresh one.

    Args:
        client: OpenRGBClient already connected instance
    """
    from effects.unified_manager import UnifiedEffectManager
    from api.effects_api import init_effects_api
    from api.devices_api import init_devices_api
    from api.keyboard_api import init_keyboard_api
    from api.monitoring_api import set_effect_manager
    from api.bindings_api import init_bindings_api
    from api.device_config_api import init_device_config_api
    from api.topology_api import init_topology_api

    import api.keyboard_api as _kbd

    old = _kbd._manager
    # 1. Nobody may write over the new manager's init (Direct mode + black):
    #    detach the ambilight (it samples but does not write without a manager)
    #    and stop the old manager's effects.
    _rewire_effect_manager(None)
    if old is not None:
        try:
            old.stop_all_effects()
        except Exception as exc:
            print(f"[WARN] Stopping the previous effect manager: {exc}")

    # 2. New manager; on failure put the old one back where it was.
    try:
        manager = UnifiedEffectManager(client)
    except Exception:
        _rewire_effect_manager(old)
        raise
    init_effects_api(_visual_library, manager)
    init_devices_api(manager, client)
    init_keyboard_api(manager, client)
    set_effect_manager(manager)  # home dashboard: openrgb_connected + devices_count
    init_bindings_api(_settings, manager)  # keybinding profile → hardware
    init_device_config_api(manager)  # per-device enable/disable
    init_topology_api(manager)  # topology editor: reload from OpenRGB
    _rewire_effect_manager(manager)  # ambilight + game events

    # 3. Close the previous connection: each "Test connection" used to leave one
    #    more client connected to OpenRGB.
    old_client = getattr(old, "client", None)
    if old_client is not None and old_client is not client:
        try:
            old_client.disconnect()
        except Exception:
            pass
    print("[OK] Hardware stack fully initialized")


def _rewire_effect_manager(manager) -> None:
    """Point the components created once at startup to `manager`.

    The ambilight service and the event processor are built in main.py and keep
    the manager they got there: without this, after a reconnection the ambilight
    asked the OLD manager whether an effect was playing (always no) and wrote
    over the effects, and game events went to the old, disconnected client.
    """
    try:
        from api import ambilight_api
        ambilight_api.set_effect_manager(manager)
    except Exception as exc:
        print(f"[WARN] Ambilight not re-wired: {exc}")
    try:
        from api import monitoring_api
        if manager is not None and monitoring_api._event_processor is not None:
            monitoring_api._event_processor.effect_manager = manager
    except Exception as exc:
        print(f"[WARN] Event processor not re-wired: {exc}")


@eel.expose
def get_available_languages():
    """Get list of available languages."""
    return {
        "en": "English",
        "it": "Italiano",
        "es": "Español",
        "de": "Deutsch",
        "fr": "Français",
    }


@eel.expose
def verify_journal_path(path):
    """Verify journal directory exists and contains journal files."""
    if not _settings:
        return {"valid": False, "message": "Settings not initialized"}

    try:
        journal_path = Path(path)

        # Check if path exists
        if not journal_path.exists():
            return {"valid": False, "message": "Path does not exist"}

        # Check if it's a directory
        if not journal_path.is_dir():
            return {"valid": False, "message": "Path is not a directory"}

        # Look for journal files (Journal.*.log pattern)
        journal_files = list(journal_path.glob("Journal.*.log"))

        if not journal_files:
            return {
                "valid": False,
                "message": "No journal files found (expected Journal.*.log)",
            }

        # Find latest file by modification time
        latest = max(journal_files, key=lambda p: p.stat().st_mtime)

        print(
            f"[OK] Journal path valid: {len(journal_files)} file(s), latest: {latest.name}"
        )
        return {
            "valid": True,
            "message": f"Found {len(journal_files)} journal file(s)",
            "latest_file": str(latest.name),
            "file_count": len(journal_files),
        }
    except Exception as e:
        print(f"[ERROR] Failed to verify journal path: {e}")
        return {"valid": False, "message": str(e)}



def _get_browser_hwnd(search_title: str = 'ED:Event2Led') -> int:
    """
    Find the HWND of the visible browser window showing the app web UI.

    Uses EnumWindows to scan all top-level windows for one whose title
    contains 'ED:Event2Led'.  Returns 0 if not found.

    This HWND is passed as the native owner of WinForms dialogs so they
    appear in front of the browser: Windows always places an owned dialog
    in front of its owner, regardless of focus-stealing prevention policy.
    """
    try:
        import ctypes, ctypes.wintypes

        result = [0]
        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

        def _cb(hwnd, _):
            if not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True
            n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if n == 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, n + 1)
            if search_title in buf.value:
                result[0] = int(hwnd)
                return False   # stop enumeration
            return True

        ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)
        return result[0]
    except Exception:
        return 0


def _native_folder_dialog(parent_hwnd: int, title: str, initial_dir: str = "") -> str:
    """
    Native Windows folder picker via SHBrowseForFolderW (ctypes, no subprocess).

    Runs in a real OS thread so the gevent hub stays unblocked while the user
    interacts with the dialog.  Polling uses gevent.sleep(0.05) to yield back
    to other greenlets between checks.

    parent_hwnd — pass _get_browser_hwnd() so the dialog is owned by the
                  browser; Windows always places an owned dialog in front of
                  its owner regardless of focus-stealing prevention policy.
    """
    import ctypes
    import ctypes.wintypes
    import threading

    _result = [None]  # None = dialog still open

    def _show():
        try:
            shell32 = ctypes.windll.shell32
            user32  = ctypes.windll.user32
            ole32   = ctypes.windll.ole32
            ole32.CoInitialize(None)   # STA required for shell dialogs

            # Callback: fires on BFFM_INITIALIZED to pre-select the initial dir
            BFFCALLBACK = ctypes.WINFUNCTYPE(
                ctypes.c_int,
                ctypes.wintypes.HWND,
                ctypes.wintypes.UINT,
                ctypes.wintypes.LPARAM,
                ctypes.wintypes.LPARAM,
            )

            _init = initial_dir or ""

            @BFFCALLBACK
            def _cb(hwnd, msg, lp, data):
                if msg == 1 and _init:   # BFFM_INITIALIZED = 1
                    # BFFM_SETSELECTIONW = WM_USER+103 = 0x0467
                    # wParam=1 (TRUE) means lParam is a path string, not a PIDL
                    path_buf = ctypes.create_unicode_buffer(_init)
                    user32.SendMessageW(hwnd, 0x0467, 1, ctypes.addressof(path_buf))
                return 0

            class BROWSEINFOW(ctypes.Structure):
                _fields_ = [
                    ('hwndOwner',      ctypes.c_void_p),
                    ('pidlRoot',       ctypes.c_void_p),
                    ('pszDisplayName', ctypes.c_void_p),
                    ('lpszTitle',      ctypes.c_wchar_p),
                    ('ulFlags',        ctypes.c_uint32),
                    ('lpfn',           BFFCALLBACK),
                    ('lParam',         ctypes.c_void_p),
                    ('iImage',         ctypes.c_int),
                ]

            display_buf = ctypes.create_unicode_buffer(260)

            bi = BROWSEINFOW()
            bi.hwndOwner      = parent_hwnd or 0
            bi.pidlRoot       = None
            bi.pszDisplayName = ctypes.addressof(display_buf)
            bi.lpszTitle      = title
            # BIF_RETURNONLYFSDIRS(0x01) | BIF_NEWDIALOGSTYLE(0x40) | BIF_EDITBOX(0x10)
            bi.ulFlags        = 0x51
            bi.lpfn           = _cb
            bi.lParam         = 0
            bi.iImage         = 0

            pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
            if pidl:
                path_buf = ctypes.create_unicode_buffer(260)
                shell32.SHGetPathFromIDListW(pidl, path_buf)
                ole32.CoTaskMemFree(pidl)
                _result[0] = path_buf.value or ""
            else:
                _result[0] = ""

            ole32.CoUninitialize()

        except Exception as exc:
            print(f"[ERROR] _native_folder_dialog: {exc}")
            _result[0] = ""

    threading.Thread(target=_show, daemon=True).start()

    try:
        import gevent as _gevent
        _sleep = _gevent.sleep
    except ImportError:
        import time as _time
        _sleep = _time.sleep

    while _result[0] is None:
        _sleep(0.05)
    return _result[0]


def _native_file_dialog(
    parent_hwnd: int,
    title: str,
    initial_dir: str = "",
    filter_pairs: list | None = None,
    default_ext: str = "",
) -> str:
    """
    Native Windows file open dialog via GetOpenFileNameW (ctypes, no subprocess).

    filter_pairs — list of (description, pattern) tuples, e.g.:
        [("Bindings files (*.binds)", "*.binds"), ("All files (*.*)", "*.*")]

    Returns the selected file path, or "" if the user cancelled.
    """
    import ctypes
    import ctypes.wintypes
    import threading

    _result = [None]

    def _show():
        try:
            comdlg32 = ctypes.windll.comdlg32
            ole32    = ctypes.windll.ole32
            ole32.CoInitialize(None)

            # Build filter string: "desc\0pattern\0desc\0pattern\0\0"
            # ctypes.create_unicode_buffer adds one extra null, giving correct
            # double-null termination expected by GetOpenFileNameW.
            pairs = filter_pairs or [("All files (*.*)", "*.*")]
            filter_str = ""
            for desc, pat in pairs:
                filter_str += desc + "\0" + pat + "\0"
            filter_str += "\0"   # ensures correct \0\0 end after ctypes appends its own null
            filter_buf = ctypes.create_unicode_buffer(filter_str)

            file_buf = ctypes.create_unicode_buffer(4096)

            class OPENFILENAMEW(ctypes.Structure):
                _fields_ = [
                    ('lStructSize',       ctypes.c_uint32),
                    ('hwndOwner',         ctypes.c_void_p),
                    ('hInstance',         ctypes.c_void_p),
                    ('lpstrFilter',       ctypes.c_void_p),   # embedded nulls → c_void_p + addressof
                    ('lpstrCustomFilter', ctypes.c_void_p),
                    ('nMaxCustFilter',    ctypes.c_uint32),
                    ('nFilterIndex',      ctypes.c_uint32),
                    ('lpstrFile',         ctypes.c_void_p),   # mutable output → c_void_p + addressof
                    ('nMaxFile',          ctypes.c_uint32),
                    ('lpstrFileTitle',    ctypes.c_void_p),
                    ('nMaxFileTitle',     ctypes.c_uint32),
                    ('lpstrInitialDir',   ctypes.c_wchar_p),  # read-only by API
                    ('lpstrTitle',        ctypes.c_wchar_p),  # read-only by API
                    ('Flags',             ctypes.c_uint32),
                    ('nFileOffset',       ctypes.c_uint16),
                    ('nFileExtension',    ctypes.c_uint16),
                    ('lpstrDefExt',       ctypes.c_wchar_p),  # read-only by API
                    ('lCustData',         ctypes.c_void_p),
                    ('lpfnHook',          ctypes.c_void_p),
                    ('lpTemplateName',    ctypes.c_void_p),
                    ('pvReserved',        ctypes.c_void_p),
                    ('dwReserved',        ctypes.c_uint32),
                    ('FlagsEx',           ctypes.c_uint32),
                ]

            ofn = OPENFILENAMEW()
            ofn.lStructSize     = ctypes.sizeof(OPENFILENAMEW)
            ofn.hwndOwner       = parent_hwnd or 0
            ofn.lpstrFilter     = ctypes.addressof(filter_buf)
            ofn.nFilterIndex    = 1
            ofn.lpstrFile       = ctypes.addressof(file_buf)
            ofn.nMaxFile        = 4096
            ofn.lpstrInitialDir = initial_dir or None
            ofn.lpstrTitle      = title
            # OFN_EXPLORER(0x80000) | OFN_FILEMUSTEXIST(0x1000) |
            # OFN_PATHMUSTEXIST(0x800) | OFN_NOCHANGEDIR(0x8)
            ofn.Flags           = 0x81808
            if default_ext:
                ofn.lpstrDefExt = default_ext

            if comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
                _result[0] = file_buf.value or ""
            else:
                _result[0] = ""

            ole32.CoUninitialize()

        except Exception as exc:
            print(f"[ERROR] _native_file_dialog: {exc}")
            _result[0] = ""

    threading.Thread(target=_show, daemon=True).start()

    try:
        import gevent as _gevent
        _sleep = _gevent.sleep
    except ImportError:
        import time as _time
        _sleep = _time.sleep

    while _result[0] is None:
        _sleep(0.05)
    return _result[0]

@eel.expose
def browse_journal_directory():
    """Open native Windows folder picker and return the selected path."""
    if not _settings:
        return ""
    try:
        initial = str(_settings.get_default_journal_directory())
        directory = _native_folder_dialog(
            parent_hwnd=_get_browser_hwnd(),
            title="Select Elite Dangerous Journal Directory",
            initial_dir=initial,
        )
        if directory:
            print(f"[OK] User selected journal dir: {directory}")
        else:
            print("[INFO] User cancelled journal directory selection")
        return directory
    except Exception as e:
        print(f"[ERROR] browse_journal_directory failed: {e}")
        return ""


@eel.expose
def get_show_welcome_modal():
    """Get whether to show the welcome modal on startup."""
    if not _settings:
        return True  # Default to showing if settings not initialized
    return _settings.get_show_welcome_modal()


@eel.expose
def set_show_welcome_modal(show: bool):
    """Set whether to show the welcome modal on startup."""
    if not _settings:
        return
    _settings.set_show_welcome_modal(show)
    print(f"[OK] Welcome modal preference saved: show={show}")


# ── Contextual Guide System API ────────────────────────────────


@eel.expose
def get_completed_guides():
    """Get dict of all completed guides.

    Returns:
        dict: {'configuration': True, 'effects': False, ...}
    """
    if not _settings:
        return {}
    return _settings.get_completed_guides()


# ── OpenRGB Reconnection (Tier 2) ────────────────────────────────


def with_openrgb_check(api_func):
    """
    Decorator for API functions requiring OpenRGB connection (Tier 2).
    Auto-checks connection and triggers async reconnect if needed.

    Usage:
        @eel.expose
        @with_openrgb_check
        def my_hardware_function(...):
            # Function only runs if OpenRGB connected
            ...
    """

    def wrapper(*args, **kwargs):
        # Check if connected (fast path)
        import api.keyboard_api as _kbd

        if _kbd._manager is not None:
            # Already connected - execute function
            try:
                return api_func(*args, **kwargs)
            except Exception as e:
                from utils.openrgb_client import OpenRGBDisconnected

                if isinstance(e, OpenRGBDisconnected):
                    # Show toast BEFORE background thread
                    try:
                        import eel

                        eel.show_reconnect_toast()
                    except:
                        pass
                    try_ensure_openrgb(notify_ui=False)  # Already showed toast
                    return {
                        "success": False,
                        "error": "Connection lost. Reconnecting...",
                    }
                else:
                    raise

        # Not connected - show toast IMMEDIATELY in main thread
        try:
            import eel

            eel.show_reconnect_toast()
        except:
            pass

        # Then trigger async reconnect (without duplicate toast)
        if not try_ensure_openrgb(notify_ui=False):
            return {"success": False, "error": "OpenRGB not connected. Reconnecting..."}

        # If we get here, reconnect completed during call (unlikely)
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}

    wrapper.__name__ = api_func.__name__
    wrapper.__doc__ = api_func.__doc__
    return wrapper


@eel.expose
def force_openrgb_reconnect():
    """
    Force immediate reconnection (ignores cooldown).
    Called from connection lost modal Retry button (Tier 3).

    Returns:
        dict: {'success': bool, 'device_count': int} or {'success': False, 'error': str}
    """
    global _last_probe_failed
    _last_probe_failed = 0.0  # Reset cooldown

    try:
        host = _settings.get_openrgb_host()
        port = _settings.get_openrgb_port()

        if not _ping_openrgb(host, port):
            return {
                "success": False,
                "error": f"OpenRGB not reachable at {host}:{port}",
            }

        from utils.openrgb_client import OpenRGBClient

        client = OpenRGBClient(host, port)
        _initialize_hardware(client)

        import api.keyboard_api as _kbd

        device_count = len(_kbd._manager.devices) if _kbd._manager else 0

        return {"success": True, "device_count": device_count}

    except Exception as e:
        _last_probe_failed = time.monotonic()
        return {"success": False, "error": str(e)}


# ── Git Info API ────────────────────────────────────────────────


import subprocess
from datetime import datetime


def _get_git_info() -> dict:
    """
    Get version and build info from git (dev) or from baked _version.py (frozen).

    In a frozen/compiled PyInstaller app:
      - git is not available (not part of the install)
      - _version.py is generated by build_pyinstaller.ps1 at build time
      - We return the baked version directly, no subprocess calls

    In development (plain Python):
      - 5 git subprocesses are spawned (CREATE_NO_WINDOW on Windows)
      - Result is cached so git is only called once per process

    Returns:
        dict: {
            'version': str,      # e.g. '1.0-11-gc92bb20' or 'compiled'
            'build_date': str,   # e.g. '2026.05.27'
            'branch': str,       # e.g. 'master' or 'release'
            'commit': str,       # short hash e.g. 'gc92bb20'
            'is_dirty': bool
        }
    """
    # ── Frozen app: use version baked in at build time ─────────────────────
    if getattr(sys, 'frozen', False):
        try:
            import _version
            ver = getattr(_version, 'VERSION', 'compiled')
            return {
                'version':    ver,
                'build_date': getattr(_version, 'BUILD_DATE', datetime.now().strftime("%Y.%m.%d")),
                'branch':     'release',
                'commit':     ver.split('-g')[-1] if '-g' in ver else '',
                'is_dirty':   False,
            }
        except ImportError:
            return {
                'version':    'compiled',
                'build_date': datetime.now().strftime("%Y.%m.%d"),
                'branch':     'release',
                'commit':     'unknown',
                'is_dirty':   False,
            }

    # ── Development: read from git ─────────────────────────────────────────
    import os

    def _run_git(args: list) -> tuple:
        try:
            extra = {}
            if sys.platform == 'win32':
                extra['creationflags'] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                ["git"] + args,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                text=True,
                timeout=5,
                **extra,
            )
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        except Exception:
            return (False, "", "")

    info = {
        "version": "1.0.0",
        "build_date": datetime.now().strftime("%Y.%m.%d"),
        "branch": "unknown",
        "commit": "unknown",
        "is_dirty": False,
    }

    # Get current branch
    success, branch, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if success:
        info["branch"] = branch

    # Get commit hash
    success, commit, _ = _run_git(["rev-parse", "--short", "HEAD"])
    if success:
        info["commit"] = commit

    # Get commit date (author date, not commit date)
    success, date_str, _ = _run_git(["log", "-1", "--format=%ci"])
    if success and date_str:
        try:
            dt = datetime.fromisoformat(date_str.split()[0])
            info["build_date"] = dt.strftime("%Y.%m.%d")
        except Exception:
            pass

    # Get version from git describe (tags)
    success, describe, _ = _run_git(["describe", "--tags", "--always", "--dirty"])
    if success:
        info["version"] = describe

    # Check for uncommitted changes
    success, status, _ = _run_git(["status", "--porcelain"])
    if success:
        info["is_dirty"] = bool(status.strip())

    return info


# Cache git info (read once at startup)
_git_info_cache: dict | None = None


def _get_cached_git_info() -> dict:
    """Get cached git info, reading from git only once."""
    global _git_info_cache
    if _git_info_cache is None:
        _git_info_cache = _get_git_info()
    return _git_info_cache


@eel.expose
def get_git_info():
    """Get version and build info from git for display in footer."""
    return _get_cached_git_info()
