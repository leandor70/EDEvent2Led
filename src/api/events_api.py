"""
Events API - Event-to-effect mapping management (v3 inline effects).

Effects are embedded inline in event_mappings.json rather than referenced
by ID from the visual_effects library. The library is only used as a source
of importable templates.
"""
import json
import eel
from pathlib import Path
from typing import List, Dict, Any

_processor = None
_library   = None

_ALL_EVENTS: List[Dict[str, Any]] = []
_EVENT_CATEGORY_MAP: Dict[str, str] = {}


def _load_event_catalog() -> None:
    global _ALL_EVENTS, _EVENT_CATEGORY_MAP
    catalog_path = Path("config/event_catalog.json")
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _ALL_EVENTS = data.get("events", [])
        _EVENT_CATEGORY_MAP = {e["name"]: e["category"] for e in _ALL_EVENTS}
        print(f"[OK] Event catalog loaded: {len(_ALL_EVENTS)} events")
    except FileNotFoundError:
        print(f"[WARNING] Event catalog not found")
    except Exception as e:
        print(f"[ERROR] Failed to load event catalog: {e}")


_load_event_catalog()


def init_events_api(processor, library):
    global _processor, _library
    _processor = processor
    _library   = library
    print("[OK] Events API initialized")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_event_category(event_name: str) -> str:
    return _EVENT_CATEGORY_MAP.get(event_name, 'Custom')


def _mapping_to_dict(event_name: str, mapping: dict) -> dict:
    """Serialize one mapping entry for the frontend."""
    effect_val = mapping.get('effect')
    # Legacy v2 fallback
    if effect_val is None and 'effect_id' in mapping:
        eid = mapping.get('effect_id', '')
        effect_val = eid if eid else None

    if isinstance(effect_val, dict):
        effect_name = effect_val.get('name', 'Unnamed')
    elif effect_val == 'keyboard_default':
        effect_name = 'Keyboard Default'
    else:
        effect_name = None

    return {
        'event_name':   event_name,
        'effect':       effect_val,
        'effect_name':  effect_name,
        'priority':     mapping.get('priority', 5),
        'enabled':      mapping.get('enabled', True),
        'category':     _get_event_category(event_name),
    }


def _effect_to_template_dict(effect) -> dict:
    """Serialize a VisualEffect from the library as a template dict."""
    d = effect.to_dict() if hasattr(effect, 'to_dict') else {}
    # Strip runtime/library-only fields
    for k in ('id', 'is_quick_created', 'created_timestamp'):
        d.pop(k, None)
    d['_template_id']   = effect.id
    d['_template_name'] = effect.name
    return d


# ── GET mappings ──────────────────────────────────────────────────────────────

@eel.expose
def get_event_mappings():
    """Return all event-to-effect mappings with inline effect data."""
    try:
        mappings = [
            _mapping_to_dict(name, m)
            for name, m in _processor.mappings.items()
        ]
        mappings.sort(key=lambda m: m['event_name'])
        return {'success': True, 'mappings': mappings, 'count': len(mappings)}
    except Exception as e:
        print(f"[ERROR] get_event_mappings: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def get_event_mapping(event_name):
    """Return a single mapping by event name."""
    try:
        if event_name not in _processor.mappings:
            return {'success': False, 'error': 'Mapping not found'}
        return {'success': True, 'mapping': _mapping_to_dict(event_name, _processor.mappings[event_name])}
    except Exception as e:
        print(f"[ERROR] get_event_mapping: {e}")
        return {'success': False, 'error': str(e)}


# ── SAVE effect inline ────────────────────────────────────────────────────────

@eel.expose
def save_event_effect(event_name: str, effect_data):
    """
    Save the effect for an event (inline dict, 'keyboard_default', or null).
    Preserves existing priority/enabled. Creates mapping if not present.
    """
    try:
        if event_name not in _processor.mappings:
            _processor.mappings[event_name] = {'priority': 5, 'enabled': True}

        _processor.mappings[event_name]['effect'] = effect_data
        _processor._update_inline_cache(event_name, effect_data)
        _processor.save_mappings()

        print(f"[OK] Effect saved inline for {event_name}")
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] save_event_effect: {e}")
        return {'success': False, 'error': str(e)}


# ── UPDATE mapping meta (priority / enabled) ──────────────────────────────────

@eel.expose
def update_event_mapping(event_name: str, mapping_data: dict):
    """
    Update priority/enabled for an event mapping.
    If 'effect' is provided in mapping_data, it is also saved inline.
    """
    try:
        if event_name not in _processor.mappings:
            _processor.mappings[event_name] = {'priority': 5, 'enabled': True, 'effect': None}

        m = _processor.mappings[event_name]
        if 'priority' in mapping_data:
            m['priority'] = int(mapping_data['priority'])
        if 'enabled' in mapping_data:
            m['enabled'] = bool(mapping_data['enabled'])
        if 'effect' in mapping_data:
            m['effect'] = mapping_data['effect']
            _processor._update_inline_cache(event_name, mapping_data['effect'])

        _processor.save_mappings()
        print(f"[OK] Mapping updated: {event_name}")
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] update_event_mapping: {e}")
        return {'success': False, 'error': str(e)}


# ── DELETE / TOGGLE ───────────────────────────────────────────────────────────

@eel.expose
def delete_event_mapping(event_name: str):
    try:
        _processor.mappings.pop(event_name, None)
        _processor._inline_cache.pop(event_name, None)
        _processor.save_mappings()
        print(f"[OK] Mapping deleted: {event_name}")
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] delete_event_mapping: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def toggle_event_mapping(event_name: str):
    try:
        if event_name not in _processor.mappings:
            return {'success': False, 'error': 'Mapping not found'}
        current = _processor.mappings[event_name].get('enabled', True)
        _processor.mappings[event_name]['enabled'] = not current
        _processor.save_mappings()
        return {'success': True, 'enabled': not current}
    except Exception as e:
        print(f"[ERROR] toggle_event_mapping: {e}")
        return {'success': False, 'error': str(e)}


# ── TEST ──────────────────────────────────────────────────────────────────────

@eel.expose
def test_event_mapping(event_name: str):
    """Test an event by triggering its configured effect on hardware."""
    try:
        if event_name not in _processor.mappings:
            return {'success': False, 'error': 'Mapping not found'}
        _processor.process_event({'event': event_name, 'timestamp': '2026-01-01T00:00:00Z'})
        mapping = _processor.mappings[event_name]
        effect_val = mapping.get('effect')
        effect_name = (effect_val.get('name') if isinstance(effect_val, dict)
                       else ('Keyboard Default' if effect_val == 'keyboard_default' else 'None'))
        return {'success': True, 'message': f'Triggered: {effect_name}'}
    except Exception as e:
        print(f"[ERROR] test_event_mapping: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def test_event_effect_live(_event_name: str, effect_data: dict):
    """Test an effect dict on hardware without saving (delegates to effects_api)."""
    try:
        from api.effects_api import test_effect_live
        return test_effect_live(effect_data)
    except Exception as e:
        print(f"[ERROR] test_event_effect_live: {e}")
        return {'success': False, 'error': str(e)}


# ── TEMPLATES (from visual_effects.json library) ───────────────────────────────

@eel.expose
def get_effect_templates():
    """Return all effects from the templates library as importable dicts."""
    try:
        effects = _library.get_all_effects()
        return {
            'success': True,
            'templates': [_effect_to_template_dict(e) for e in effects]
        }
    except Exception as e:
        print(f"[ERROR] get_effect_templates: {e}")
        return {'success': False, 'error': str(e)}


# ── CATALOG ───────────────────────────────────────────────────────────────────

@eel.expose
def get_available_events():
    """Return all known Elite Dangerous events."""
    return {'success': True, 'events': _ALL_EVENTS}


@eel.expose
def get_available_effects():
    """Return library effects list (legacy — use get_effect_templates for new code)."""
    try:
        effects = _library.get_all_effects()
        return {
            'success': True,
            'effects': [{'id': e.id, 'name': e.name, 'description': e.description,
                         'steps_count': len(e.steps)} for e in effects]
        }
    except Exception as e:
        print(f"[ERROR] get_available_effects: {e}")
        return {'success': False, 'error': str(e)}
