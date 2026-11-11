"""
Game Status API - Real-time Status.json flag state + effect assignment.

Status mappings use inline effect dicts (v2 format):
  { "Overheating": { "enabled": true, "on_effect": {...}, "off_effect": null } }

Legacy v1 format (on_effect_id / off_effect_id) is read-only supported.
"""
import eel
import json
from pathlib import Path

_status_monitor  = None
_event_processor = None

_MAPPINGS_FILE = Path('config/status_mappings.json')


# ── Mappings helpers ──────────────────────────────────────────────────────────

def _load_mappings() -> dict:
    try:
        return json.loads(_MAPPINGS_FILE.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return {'version': 2, 'mappings': {}}


def _save_mappings(data: dict):
    _MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MAPPINGS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8'
    )


def _resolve_effect_name(effect_val) -> str:
    if isinstance(effect_val, dict):
        return effect_val.get('name', 'Unnamed')
    if effect_val == 'keyboard_default':
        return 'Keyboard Default'
    return ''


# ── Init ─────────────────────────────────────────────────────────────────────

def init_status_monitor_api(status_monitor, event_processor=None):
    global _status_monitor, _event_processor
    _status_monitor  = status_monitor
    _event_processor = event_processor
    print("[OK] Game Status API initialized")


# ── Real-time status ─────────────────────────────────────────────────────────

@eel.expose
def get_game_status():
    """
    Return a real-time snapshot of the current game state.

    Each flag includes 'on_effect' and 'off_effect' (inline dicts or null)
    from status_mappings.json.
    """
    if _status_monitor is None:
        return {'monitoring': False, 'flags': 0, 'flags2': 0,
                'ship_flags': [], 'odyssey_flags': []}

    flags  = _status_monitor.current_flags
    flags2 = _status_monitor.current_flags2
    try:
        if _status_monitor.status_path.exists():
            with open(_status_monitor.status_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            flags  = raw.get('Flags',  flags)
            flags2 = raw.get('Flags2', flags2)
    except Exception:
        pass

    data     = _load_mappings()
    version  = data.get('version', 1)
    mappings = data.get('mappings', {})

    def _flag(bit, config, raw_flags):
        name    = config['name']
        mapping = mappings.get(name, {})

        if version >= 2:
            on_effect  = mapping.get('on_effect')
            off_effect = mapping.get('off_effect')
        else:
            # Legacy v1: return IDs as-is so frontend can handle both
            on_effect  = mapping.get('on_effect_id')
            off_effect = mapping.get('off_effect_id')

        return {
            'name':             name,
            'priority':         config['priority'],
            'active':           bool(raw_flags & (1 << bit)),
            'bit':              bit,
            'on_effect':        on_effect,
            'off_effect':       off_effect,
            'on_effect_name':   _resolve_effect_name(on_effect),
            'off_effect_name':  _resolve_effect_name(off_effect),
            'enabled':          mapping.get('enabled', True),
        }

    return {
        'monitoring':    _status_monitor.running,
        'flags':         flags,
        'flags2':        flags2,
        'ship_flags':    [_flag(bit, cfg, flags)
                          for bit, cfg in sorted(_status_monitor.MONITORED_FLAGS.items())],
        'odyssey_flags': [_flag(bit, cfg, flags2)
                          for bit, cfg in sorted(_status_monitor.MONITORED_FLAGS2.items())],
    }


# ── Status mappings CRUD ──────────────────────────────────────────────────────

@eel.expose
def get_status_mappings():
    """Return all status flag -> effect assignments (v2 inline format)."""
    return {'success': True, 'mappings': _load_mappings().get('mappings', {})}


@eel.expose
def set_status_flag_mapping(flag_name: str, on_effect, off_effect, enabled: bool = True):
    """
    Assign on/off inline effects to a status flag.

    on_effect / off_effect: inline effect dict | 'keyboard_default' | None
    """
    try:
        data = _load_mappings()
        data['version'] = 2
        data['mappings'][flag_name] = {
            'on_effect':  on_effect  if on_effect  else None,
            'off_effect': off_effect if off_effect else None,
            'enabled':    bool(enabled),
        }
        _save_mappings(data)

        # Update event_processor inline cache
        if _event_processor:
            _event_processor._cache_status_effect(flag_name, 'on',  on_effect)
            _event_processor._cache_status_effect(flag_name, 'off', off_effect)

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def save_status_slot(flag_name: str, slot: str, effect_data):
    """
    Save only one slot ('on' or 'off') for a status flag, preserving the other.

    effect_data: inline effect dict | 'keyboard_default' | None
    """
    try:
        if slot not in ('on', 'off'):
            return {'success': False, 'error': 'slot must be "on" or "off"'}

        data = _load_mappings()
        data['version'] = 2
        mapping = data['mappings'].setdefault(flag_name, {'enabled': True,
                                                           'on_effect': None,
                                                           'off_effect': None})
        mapping[f'{slot}_effect'] = effect_data if effect_data else None
        _save_mappings(data)

        if _event_processor:
            _event_processor._cache_status_effect(flag_name, slot, effect_data)

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def test_status_effect_live(_flag_name: str, _slot: str, effect_data: dict):
    """Test a status slot effect on hardware without saving."""
    try:
        from api.effects_api import test_effect_live
        return test_effect_live(effect_data)
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def clear_status_flag_mapping(flag_name: str):
    """Remove the effect assignment for a status flag."""
    try:
        data = _load_mappings()
        data['mappings'].pop(flag_name, None)
        _save_mappings(data)
        if _event_processor:
            _event_processor._inline_status_cache.pop(flag_name, None)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}
