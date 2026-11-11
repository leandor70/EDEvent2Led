"""
Monitoring API - Journal reading control and real-time system status.

Manages start/stop of the JournalReader and provides the status
data consumed by the Home dashboard (get_monitoring_status).
"""
import eel
from pathlib import Path
from typing import Optional

# ── Module-level references (set by init_monitoring_api) ──────────────────
_settings        = None
_event_processor = None
_effect_manager  = None
_journal_reader  = None   # JournalReader instance, created on start_monitoring()

# Last journal event seen — shown in the dashboard "Last Event" card
_last_event = {
    'name':      None,
    'effect':    None,   # effect name if a mapping fired, else None
    'timestamp': None,   # ISO timestamp from the journal line
}


def init_monitoring_api(settings, event_processor, effect_manager=None):
    """
    Initialize monitoring API.

    Args:
        settings:        Settings instance (for journal directory)
        event_processor: EventProcessor instance (processes events → RGB effects)
        effect_manager:  UnifiedEffectManager (for device count / connection status)
    """
    global _settings, _event_processor, _effect_manager
    _settings        = settings
    _event_processor = event_processor
    _effect_manager  = effect_manager
    print("[OK] Monitoring API initialized")


def set_effect_manager(manager):
    """Update the effect manager reference after a lazy OpenRGB reconnection."""
    global _effect_manager
    _effect_manager = manager


# ── Internal callback ──────────────────────────────────────────────────────

def _on_journal_event(event: dict):
    """
    Called by JournalReader for every new line in the journal.
    Updates the dashboard state, then delegates to EventProcessor.
    """
    global _last_event

    event_name = event.get('event', 'Unknown')

    # Resolve mapped effect name (if any)
    effect_name = None
    if _event_processor and event_name in _event_processor.mappings:
        mapping = _event_processor.mappings[event_name]
        if mapping.get('enabled', True):
            effect_id = mapping.get('effect_id', '')
            if effect_id and _effect_manager and hasattr(_effect_manager, 'visual_library'):
                eff = _effect_manager.visual_library.get_effect(effect_id)
                if eff:
                    effect_name = eff.name

    _last_event = {
        'name':      event_name,
        'effect':    effect_name,
        'timestamp': event.get('timestamp'),
    }

    # Trigger RGB effects via EventProcessor
    if _event_processor:
        _event_processor.process_event(event)


# ── Eel-exposed functions ──────────────────────────────────────────────────

@eel.expose
def start_monitoring():
    """
    Start watching the Elite Dangerous journal directory.

    Creates a JournalReader pointed at the configured journal path,
    initialises it (reads the latest journal file from the beginning),
    and starts the watchdog observer thread.

    Returns:
        dict: { success, message, journal_directory }
    """
    global _journal_reader

    if _journal_reader is not None and _journal_reader.is_running():
        return {'success': False, 'message': 'Monitoring already running'}

    if not _settings:
        return {'success': False, 'message': 'Settings not initialized'}

    # Resolve journal directory
    journal_dir = _settings.get_journal_directory() or _settings.get_default_journal_directory()

    try:
        from journal.journal_reader import JournalReader
        from utils.log_buffer import log_entry

        _journal_reader = JournalReader(journal_dir, _on_journal_event)
        _journal_reader.start()

        log_entry('info', 'SYSTEM', f"Journal monitoring started: {journal_dir}")
        print(f"[OK] Monitoring started: {journal_dir}")
        return {
            'success':           True,
            'message':           'Monitoring started',
            'journal_directory': journal_dir,
        }

    except ValueError as e:
        # Journal directory does not exist
        return {'success': False, 'message': str(e)}
    except Exception as e:
        print(f"[ERROR] start_monitoring: {e}")
        return {'success': False, 'message': f'Error: {e}'}


@eel.expose
def stop_monitoring():
    """
    Stop the journal watchdog observer.

    Returns:
        dict: { success, message }
    """
    global _journal_reader

    if _journal_reader is None or not _journal_reader.is_running():
        return {'success': False, 'message': 'Monitoring is not running'}

    try:
        from utils.log_buffer import log_entry
        _journal_reader.stop()
        _journal_reader = None
        log_entry('info', 'SYSTEM', 'Journal monitoring stopped')
        print("[OK] Monitoring stopped")
        return {'success': True, 'message': 'Monitoring stopped'}

    except Exception as e:
        print(f"[ERROR] stop_monitoring: {e}")
        return {'success': False, 'message': f'Error: {e}'}


@eel.expose
def get_monitoring_status():
    """
    Return a status snapshot consumed by the Home dashboard every 2 seconds.

    Returns:
        dict: {
            is_monitoring:     bool,
            journal_file:      str | None,   current journal filename
            journal_directory: str | None,
            openrgb_connected: bool,
            devices_count:     int,
            mappings_count:    int,
            last_event: {
                name:      str | None,
                effect:    str | None,
                timestamp: str | None,
            }
        }
    """
    is_monitoring = _journal_reader is not None and _journal_reader.is_running()

    # Current journal filename (short name only)
    journal_file = None
    if is_monitoring and _journal_reader.event_handler and \
            _journal_reader.event_handler.current_journal:
        journal_file = _journal_reader.event_handler.current_journal.name

    # Journal directory
    journal_dir = None
    if _settings:
        journal_dir = _settings.get_journal_directory() or \
                      _settings.get_default_journal_directory()

    # OpenRGB status
    openrgb_connected = _effect_manager is not None
    devices_count = len(_effect_manager.devices) \
        if openrgb_connected and hasattr(_effect_manager, 'devices') else 0

    # Mappings count
    mappings_count = len(_event_processor.mappings) if _event_processor else 0

    return {
        'is_monitoring':     is_monitoring,
        'journal_file':      journal_file,
        'journal_directory': journal_dir,
        'openrgb_connected': openrgb_connected,
        'devices_count':     devices_count,
        'mappings_count':    mappings_count,
        'last_event':        dict(_last_event),
    }
