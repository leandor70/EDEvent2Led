"""
ED:Event2Led - Main entry point.
"""
import sys
import os
import threading
import webbrowser
import eel
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.paths import get_base_dir
from settings import Settings

# Set CWD to base dir so all relative paths (config/, log/) resolve correctly
# whether running as a script or as a PyInstaller-frozen .exe.
os.chdir(get_base_dir())

# Start file logger as early as possible so startup messages are captured.
from utils.log_buffer import init_file_logger
init_file_logger("log")

# ── Init state (shared between main thread and background init) ────────────
# The loading page polls get_init_status() every 350ms.
# The background thread updates this dict as each step completes.
_init_status = {
    'ready':   False,
    'message': 'Starting...',
    'step':    0,
    'total':   5,
    'error':   None,
}

# ── Shutdown timer ─────────────────────────────────────────────────────────
# Set when all WebSocket connections drop. Cancelled if a new connection
# arrives before it fires (e.g. browser navigating between pages).
# When the system tray is active, browser-close does NOT trigger shutdown.
SHUTDOWN_DELAY_SECS = 15
_shutdown_timer = None

# ── Status monitor reference (set by _do_init, read by _do_shutdown) ───────
_status_monitor = None

# ── System tray ─────────────────────────────────────────────────────────────
_tray_icon   = None   # pystray.Icon instance (None if unavailable)
_tray_active = False  # True once the tray is running
_web_port    = 8000   # Set in main() before tray starts


def _create_tray_image():
    """Create the system tray icon programmatically (PIL).
    Returns a 64×64 RGBA image with the app's amber-on-dark aesthetic."""
    from PIL import Image, ImageDraw
    size = 64
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer amber circle
    draw.ellipse([2, 2, size - 2, size - 2], fill=(200, 100, 0, 255))
    # Inner dark circle
    draw.ellipse([10, 10, size - 10, size - 10], fill=(18, 18, 18, 255))
    # Three horizontal bars (stylised "E" / LED strip motif)
    bar_x0, bar_x1 = 18, 46
    for cy in [22, 32, 42]:
        draw.rectangle([bar_x0, cy - 3, bar_x1, cy + 3], fill=(220, 110, 0, 255))
    return img


def _open_browser_from_tray(icon=None, item=None):
    webbrowser.open(f'http://localhost:{_web_port}')


def _exit_app(icon=None, item=None):
    """Clean shutdown callable from both the tray menu and the timer."""
    global _tray_icon
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    if _status_monitor is not None:
        try:
            _status_monitor.stop()
        except Exception:
            pass
    os._exit(0)


def _start_tray(language: str = 'en'):
    """Start the system tray icon in a detached (non-blocking) thread."""
    global _tray_icon, _tray_active
    try:
        import pystray
        from i18n import I18n
        i18n = I18n(language)
        menu = pystray.Menu(
            pystray.MenuItem('ED:Event2Led', None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(i18n.t('tray_open_browser'), _open_browser_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(i18n.t('tray_exit'), _exit_app),
        )
        _tray_icon = pystray.Icon(
            name='EDEvent2Led',
            icon=_create_tray_image(),
            title='ED:Event2Led',
            menu=menu,
        )
        _tray_active = True
        _tray_icon.run_detached()
        print(f"[OK] System tray icon started (language: {language})")
    except Exception as e:
        print(f"[WARNING] System tray not available: {e}")
        _tray_active = False


@eel.expose
def get_init_status():
    """Called by loading.html to track initialization progress."""
    return dict(_init_status)


@eel.expose
def cancel_shutdown():
    """
    Called by any page on load to cancel a pending shutdown timer.
    Needed because close_callback fires only on disconnect, not on reconnect —
    so a page navigating to another page would start the timer and nothing
    would cancel it unless the new page explicitly calls this.
    """
    global _shutdown_timer
    if _shutdown_timer is not None:
        _shutdown_timer.cancel()
        _shutdown_timer = None
        print("[INFO] Shutdown cancelled - browser reconnected.")


def _set_step(step, message):
    """Update init status. Called from the background init thread."""
    _init_status['step'] = step
    _init_status['message'] = message
    print(f"  [{step}/5] {message}")


def _do_init(settings):
    """
    Heavy initialization in a background thread so the Eel server
    (started with block=False) can respond to loading.html immediately.

    Steps:
      1 - Load visual effect library (JSON)
      2 - Connect to OpenRGB, enumerate devices
      3 - Initialize event processor and load mappings
      4 - Register all API endpoints
      5 - Ready
    """
    try:
        # ── Step 1: Effect library ─────────────────────────────────────────
        _set_step(1, 'Loading effect library...')
        from core.visual_effect_library import VisualEffectLibrary
        visual_library = VisualEffectLibrary()
        print(f"       {len(visual_library.get_all_effects())} effects loaded")

        # ── Step 2: OpenRGB connection ─────────────────────────────────────
        _set_step(2, 'Connecting to OpenRGB...')
        effect_manager = None
        client = None
        try:
            import socket as _socket
            # Quick reachability check before creating the full client
            _sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            _sock.settimeout(1)
            _sock.connect((settings.get_openrgb_host(), settings.get_openrgb_port()))
            _sock.close()

            from utils.openrgb_client import OpenRGBClient
            from effects.unified_manager import UnifiedEffectManager
            client = OpenRGBClient(settings.get_openrgb_host(), settings.get_openrgb_port())
            effect_manager = UnifiedEffectManager(client)
            device_count = len(effect_manager.devices) if hasattr(effect_manager, 'devices') else 0
            print(f"       OpenRGB connected - {device_count} device(s)")
        except _socket.timeout:
            print(f"       OpenRGB timeout (1s) - continuing without hardware")
        except Exception as e:
            print(f"       OpenRGB not available: {e}")

        # ── Step 3: Event processor ────────────────────────────────────────
        _set_step(3, 'Initializing event processor...')
        from journal.event_processor import EventProcessor
        event_processor = EventProcessor(effect_manager)
        event_processor.load_mappings()  # Load event-to-effect mappings
        print(f"       {len(event_processor.mappings)} event mappings loaded")

        # ── Step 3b: Status Monitor ────────────────────────────────────────
        global _status_monitor
        try:
            from journal.status_monitor import StatusMonitor
            _journal_dir = settings.get_journal_directory() or settings.get_default_journal_directory()
            _status_file = Path(_journal_dir) / 'Status.json'
            _status_monitor = StatusMonitor(
                status_file_path=str(_status_file),
                callback=event_processor.process_status_flag
            )
            if _status_monitor.start():
                print(f'       Status monitor started: {_status_file.name}')
            else:
                print(f'       Status monitor: Status.json not found yet (will activate on game start)')
        except Exception as e:
            print(f'       Status monitor error: {e}')
            _status_monitor = None

        # ── Step 4: APIs ───────────────────────────────────────────────────
        _set_step(4, 'Starting API services...')
        from utils.log_buffer import init_log_buffer, log_entry
        init_log_buffer(eel)

        from api.settings_api    import init_settings_api
        from api.effects_api     import init_effects_api
        from api.events_api      import init_events_api
        from api.devices_api     import init_devices_api
        from api.keyboard_api    import init_keyboard_api
        from api.profiles_api    import init_profiles_api
        from api.logs_api        import init_logs_api
        from api.device_config_api import init_device_config_api
        from api.monitoring_api     import init_monitoring_api
        from api.bindings_api       import init_bindings_api
        from api.status_monitor_api import init_status_monitor_api
        from api.topology_api    import init_topology_api
        from api.ambilight_api   import init_ambilight_api

        init_settings_api(settings, visual_library)
        init_effects_api(visual_library, effect_manager)
        init_events_api(event_processor, visual_library)
        init_devices_api(effect_manager, client if effect_manager else None)
        init_keyboard_api(effect_manager, client if effect_manager else None)
        init_profiles_api(visual_library, event_processor)
        init_logs_api()
        init_device_config_api(effect_manager)
        init_monitoring_api(settings, event_processor, effect_manager)
        init_bindings_api(settings, effect_manager)
        init_status_monitor_api(_status_monitor, event_processor)
        init_topology_api(effect_manager)  # Pass effect_manager for OpenRGB sync

        from effects.ambilight_service import AmbilightService
        _ambilight_svc = AmbilightService(effect_manager)
        _ambilight_svc.start()
        init_ambilight_api(_ambilight_svc, effect_manager)

        # Startup log entries (visible in the Logs page)
        log_entry('info', 'SYSTEM', 'ED:Event2Led started')
        log_entry('info', 'SYSTEM',
                  f"Visual Effect Library: {len(visual_library.get_all_effects())} effects loaded")
        if effect_manager:
            device_count = len(effect_manager.devices) if hasattr(effect_manager, 'devices') else 0
            log_entry('info', 'OPENRGB',
                      f"Connected to OpenRGB at {settings.get_openrgb_host()}:{settings.get_openrgb_port()} ({device_count} devices)")
        else:
            log_entry('warning', 'OPENRGB',
                      f"OpenRGB not available at {settings.get_openrgb_host()}:{settings.get_openrgb_port()}")
        log_entry('info', 'SYSTEM', f"Event mappings: {len(event_processor.mappings)} loaded")

        # ── Step 5: Ready ──────────────────────────────────────────────────
        _set_step(5, 'Ready!')
        _init_status['ready'] = True
        print()
        print("[OK] Initialization complete - loading.html will redirect to index.html")

    except Exception as e:
        import traceback
        traceback.print_exc()
        _init_status['error'] = str(e)
        _init_status['message'] = f'Initialization error: {e}'
        print(f"[ERROR] Initialization failed: {e}")


def _on_browser_close(route, websockets):
    """
    Called by Eel every time a WebSocket connection closes.

    Two distinct cases:
      - websockets is non-empty: another tab/page is still connected
        (e.g. mid-navigation from loading.html to index.html) — do nothing.
      - websockets is empty: the last connection dropped. Start a countdown.
        If nobody reconnects within SHUTDOWN_DELAY_SECS, exit cleanly.
        If a new connection arrives before the timer fires (page reload,
        navigation), cancel the timer.
    """
    global _shutdown_timer

    # Leaving the page (navigation, reload, window close) must not leave an
    # active topology calibration driving the LEDs with the ambilight paused.
    # The client-side pagehide call is best effort; this is the reliable path.
    # No-op when no calibration is running.
    try:
        from api.topology_api import stop_topology_calibration
        stop_topology_calibration()
    except Exception as e:
        print(f"[WARNING] Could not stop topology calibration on disconnect: {e}")

    if websockets:
        # A connection arrived while we were counting down — cancel shutdown
        if _shutdown_timer is not None:
            _shutdown_timer.cancel()
            _shutdown_timer = None
        return

    # All connections dropped.
    if _tray_active:
        # Tray is running: keep the app alive so the user can reopen the browser.
        print("[INFO] Browser disconnected. App continues in system tray.")
        return

    # No tray — start the 15s auto-shutdown countdown.
    print(f"[INFO] Browser disconnected. Shutting down in {SHUTDOWN_DELAY_SECS}s "
          f"unless reconnected...")

    _shutdown_timer = threading.Timer(SHUTDOWN_DELAY_SECS, _exit_app)
    _shutdown_timer.daemon = True
    _shutdown_timer.start()


def main():
    """Main application entry point."""
    print("=" * 60)
    print("ED:Event2Led - Eel Web UI")
    print("=" * 60)
    print()

    global _web_port

    # Load settings — lightweight, always done first
    settings = Settings()
    print("[OK] Settings loaded")

    # Initialize Eel immediately so the server can serve loading.html
    web_folder = get_base_dir() / 'web'
    eel.init(str(web_folder))
    print(f"[OK] Eel initialized  ({web_folder})")

    # Start Eel with loading.html using block=False.
    # eel.start() returns only after the server socket is bound and listening —
    # so by the time the next line runs the server is guaranteed to be up.
    web_port = settings.get_web_port()
    _web_port = web_port
    eel.start(
        'loading.html',
        size=(1400, 800),
        port=web_port,
        mode=None,       # We open the browser ourselves (see webbrowser.open below)
        block=False,     # Return immediately — don't wait for browser to close
        shutdown_delay=30,
        close_callback=_on_browser_close,
    )

    # Server is UP — start tray icon and open the browser.
    language = settings.settings.get('language', 'en')
    _start_tray(language)
    webbrowser.open(f'http://localhost:{web_port}/loading.html')

    print()
    print(f"[OK] Server started - http://localhost:{web_port}/loading.html")
    print("[OK] Browser opened")
    print("[OK] Background initialization starting...")
    print()

    # Heavy initialization in a background daemon thread.
    # The loading page polls get_init_status() while this runs.
    init_thread = threading.Thread(
        target=_do_init,
        args=(settings,),
        daemon=True,
        name='ed-init',
    )
    init_thread.start()

    # Keep the gevent event loop alive.
    # eel.sleep() yields control to gevent so HTTP/WebSocket requests
    # are processed while init runs in the background thread.
    try:
        while True:
            eel.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user (Ctrl+C). Goodbye.")
        _exit_app()


if __name__ == '__main__':
    main()
