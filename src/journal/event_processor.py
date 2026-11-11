"""
Event Processor Module.
Maps Elite Dangerous journal events and Status.json flags to RGB effects.

Effects are stored inline in event_mappings.json (v3) and
status_mappings.json (v2) — no external library lookup required at runtime.
"""
import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

from effects.unified_manager import UnifiedEffectManager
from utils.log_buffer import log_entry


class EventProcessor:
    """
    Processes Elite Dangerous events and status flags, triggers RGB effects.

    Usage:
        processor = EventProcessor(effect_manager)
        processor.load_mappings("config/event_mappings.json")
        processor.process_event(event_dict)
    """

    # Events that carry a directional sub-field.
    _DIRECTIONAL_FIELDS: Dict[str, str] = {
        'UnderAttack': 'Side',   # values: Front | Right | Left | Rear
    }

    def __init__(self, effect_manager: UnifiedEffectManager):
        self.effect_manager = effect_manager
        self.mappings: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.active_effects = {}
        self.active_status_effects = {}

        # Runtime caches: event_name / flag_name → VisualEffect object
        self._inline_cache: Dict[str, Any] = {}
        self._inline_status_cache: Dict[str, Dict[str, Any]] = {}  # flag → {"on": ve, "off": ve}

        # Thread-safety — priority enforcement (Intervento 1)
        self._current_priority: int = 0
        self._priority_expiry: float = 0.0

        # Thread-safety — burst debounce (Intervento 3)
        self._last_event_time: Dict[str, float] = {}
        self._DEBOUNCE_MS: float = 200.0

    # ── Mappings load / save ──────────────────────────────────────────────────

    def load_mappings(self, config_file: str = "config/event_mappings.json") -> bool:
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"Warning: Config file not found: {config_file}")
            return False

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            version = data.get('version', 2)
            raw = data.get('mappings', {})

            self.mappings = {}
            self._inline_cache = {}

            if version < 3:
                # Legacy v2: keep as-is for compatibility, effect_id path still works
                self.mappings = raw
            else:
                self._load_v3_mappings(raw)

            print(f"[EventProcessor] Loaded {len(self.mappings)} event mappings (v{version})")
            log_entry('info', 'SYSTEM', f"Event mappings loaded: {len(self.mappings)} entries")
            return True

        except Exception as e:
            print(f"[EventProcessor] ERROR: Could not load config file: {e}")
            log_entry('error', 'ERROR', f"Could not load mappings file: {e}")
            return False

    def _load_v3_mappings(self, raw: dict):
        """Parse v3 format: effect is an inline dict, 'keyboard_default', or null."""
        from core.base_effects import VisualEffect
        for event_name, m in raw.items():
            effect_val = m.get('effect')
            self.mappings[event_name] = {
                'priority': m.get('priority', 5),
                'enabled':  m.get('enabled', True),
                'effect':   effect_val,
            }
            if isinstance(effect_val, dict):
                try:
                    ve = VisualEffect.from_dict({**effect_val, 'id': f'_ev_{event_name}'})
                    self._inline_cache[event_name] = ve
                except Exception as e:
                    print(f"[EventProcessor] WARNING: could not parse inline effect for {event_name}: {e}")

    def save_mappings(self, config_file: str = "config/event_mappings.json") -> bool:
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            serialized = {}
            for event_name, m in self.mappings.items():
                effect_val = m.get('effect')
                # If legacy v2 mapping still has effect_id, convert on save
                if 'effect_id' in m and 'effect' not in m:
                    effect_val = m.get('effect_id')  # will be null if missing
                serialized[event_name] = {
                    'priority': m.get('priority', 5),
                    'enabled':  m.get('enabled', True),
                    'effect':   effect_val,
                }

            data = {'version': 3, 'mappings': serialized}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[EventProcessor] Saved {len(self.mappings)} event mappings")
            return True

        except Exception as e:
            print(f"[EventProcessor] ERROR: Could not save config file: {e}")
            return False

    def _update_inline_cache(self, event_name: str, effect_val):
        """Update inline cache after an API write."""
        if isinstance(effect_val, dict):
            try:
                from core.base_effects import VisualEffect
                ve = VisualEffect.from_dict({**effect_val, 'id': f'_ev_{event_name}'})
                self._inline_cache[event_name] = ve
            except Exception as e:
                print(f"[EventProcessor] WARNING: cache update failed for {event_name}: {e}")
        else:
            self._inline_cache.pop(event_name, None)

    # ── add/remove helpers (kept for API compat) ──────────────────────────────

    def add_mapping(self, event_name: str, effect_id: str,
                    enabled: bool = True, priority: int = 5,
                    devices: Optional[list] = None):
        """Legacy helper — stores effect_id field (v2 path)."""
        self.mappings[event_name] = {
            'effect_id': effect_id,
            'enabled': enabled,
            'priority': priority,
            'devices': devices,
        }

    def remove_mapping(self, event_name: str):
        if event_name in self.mappings:
            del self.mappings[event_name]
        self._inline_cache.pop(event_name, None)

    def get_mapping(self, event_name: str) -> Optional[Dict[str, Any]]:
        return self.mappings.get(event_name)

    # ── Event processing ──────────────────────────────────────────────────────

    def process_event(self, event: Dict[str, Any]):
        event_name = event.get('event')
        if not event_name:
            return

        log_entry('info', 'EVENT', f"Detected: {event_name}")

        # Directional compound key (e.g. "UnderAttack_Right")
        if event_name in self._DIRECTIONAL_FIELDS:
            field = self._DIRECTIONAL_FIELDS[event_name]
            sub_value = event.get(field, '')
            if sub_value:
                compound = f"{event_name}_{sub_value}"
                if compound in self.mappings:
                    event_name = compound

        mapping = self.get_mapping(event_name)
        if not mapping or not mapping.get('enabled', True):
            return

        priority = mapping.get('priority', 5)
        devices  = mapping.get('devices')
        now = time.time()

        # Debounce: skip same event if it fired within _DEBOUNCE_MS (burst protection)
        if now - self._last_event_time.get(event_name, 0.0) < self._DEBOUNCE_MS / 1000.0:
            log_entry('info', 'EVENT', f"Debounce skip: {event_name}")
            return

        # Priority: skip if a higher-priority effect is still playing
        if now < self._priority_expiry and priority < self._current_priority:
            log_entry('info', 'EVENT',
                      f"Priority skip: {event_name} (p{priority} < active p{self._current_priority})")
            return

        self._last_event_time[event_name] = now

        target_devices = None
        if devices is not None and self.effect_manager:
            target_devices = [
                self.effect_manager.devices[idx]
                for idx in devices
                if 0 <= idx < len(self.effect_manager.devices)
            ]

        if not self.effect_manager:
            print(f"[EventProcessor] WARNING: effect_manager is None")
            return

        if len(self.effect_manager.devices) == 0:
            print(f"[EventProcessor] WARNING: No OpenRGB devices")
            log_entry('warning', 'WARNING', f"No devices for event '{event_name}'")
            return

        # Update priority tracking — estimate total finite-step duration
        _effect_ms = 3000
        if event_name in self._inline_cache:
            _ve = self._inline_cache[event_name]
            _finite = [s for s in _ve.steps if not s.params.loop_infinite]
            if _finite:
                _effect_ms = sum(s.params.duration_ms or 1000 for s in _finite)
        self._current_priority = priority
        self._priority_expiry = now + _effect_ms / 1000.0

        # ── v3 inline path ──
        if event_name in self._inline_cache:
            ve = self._inline_cache[event_name]
            print(f"[EventProcessor] Triggering '{ve.name}' (inline) for '{event_name}' (priority {priority})")
            log_entry('info', 'RENDER', f"Triggering '{ve.name}' for {event_name}")
            try:
                self.effect_manager.play_visual_effect_object(ve, devices=target_devices)
            except Exception as e:
                print(f"[EventProcessor] ERROR triggering inline effect: {e}")
                log_entry('error', 'ERROR', f"Failed inline effect for {event_name}: {e}")
            return

        effect_val = mapping.get('effect')
        if effect_val == 'keyboard_default':
            print(f"[EventProcessor] Triggering keyboard_default for '{event_name}'")
            log_entry('info', 'RENDER', f"Triggering keyboard_default for {event_name}")
            try:
                self.effect_manager.play_visual_effect('keyboard_default', devices=target_devices)
            except Exception as e:
                print(f"[EventProcessor] ERROR triggering keyboard_default: {e}")
            return

        # ── v2 legacy path: effect_id ──
        effect_id = mapping.get('effect_id')
        if not effect_id:
            return

        effect_name = effect_id
        try:
            ve = self.effect_manager.visual_library.get_effect(effect_id)
            if ve:
                effect_name = ve.name
        except Exception:
            pass
        print(f"[EventProcessor] Triggering '{effect_name}' ({effect_id}) for '{event_name}'")
        log_entry('info', 'RENDER', f"Triggering '{effect_name}' for {event_name}")
        try:
            self.effect_manager.play_visual_effect(effect_id, devices=target_devices)
        except Exception as e:
            print(f"[EventProcessor] ERROR triggering effect: {e}")
            log_entry('error', 'ERROR', f"Failed effect '{effect_id}' for {event_name}: {e}")

    # ── Status flag processing ────────────────────────────────────────────────

    @staticmethod
    def _load_status_mappings() -> dict:
        try:
            return json.loads(
                Path('config/status_mappings.json').read_text(encoding='utf-8')
            )
        except Exception:
            return {'version': 1, 'mappings': {}}

    def _get_status_ve(self, flag_name: str, slot: str):
        """Return cached VisualEffect for a status flag slot ('on'/'off'), or None."""
        cached = self._inline_status_cache.get(flag_name, {})
        return cached.get(slot)

    def _cache_status_effect(self, flag_name: str, slot: str, effect_val):
        """Parse and cache an inline effect for a status flag slot."""
        if not isinstance(effect_val, dict):
            self._inline_status_cache.setdefault(flag_name, {}).pop(slot, None)
            return
        try:
            from core.base_effects import VisualEffect
            ve = VisualEffect.from_dict({**effect_val, 'id': f'_st_{flag_name}_{slot}'})
            self._inline_status_cache.setdefault(flag_name, {})[slot] = ve
        except Exception as e:
            print(f"[EventProcessor] WARNING: status cache failed {flag_name}.{slot}: {e}")

    def _prime_status_cache(self, mappings_data: dict):
        """Pre-populate status inline cache from loaded mappings (v2 format)."""
        version = mappings_data.get('version', 1)
        if version < 2:
            return
        for flag_name, m in mappings_data.get('mappings', {}).items():
            self._cache_status_effect(flag_name, 'on',  m.get('on_effect'))
            self._cache_status_effect(flag_name, 'off', m.get('off_effect'))

    def process_status_flag(self, flag_name: str, is_active: bool,
                            _legacy_effect_id: str, _priority: int):
        """
        Process a Status.json flag change and trigger the configured RGB effect.

        Effect assignments come from config/status_mappings.json.
        Supports both v2 (inline dict) and v1 (effect_id) formats.
        """
        mappings_data = self._load_status_mappings()
        mappings = mappings_data.get('mappings', {})
        version  = mappings_data.get('version', 1)
        mapping  = mappings.get(flag_name, {})

        if not mapping.get('enabled', True):
            return

        # Prime cache on first access for this flag
        if flag_name not in self._inline_status_cache and version >= 2:
            self._prime_status_cache(mappings_data)

        with self.lock:
            if is_active:
                self._play_status_slot(flag_name, 'on', mapping, version)
                self.active_status_effects[flag_name] = flag_name
            else:
                has_off = self._play_status_slot(flag_name, 'off', mapping, version)
                if not has_off:
                    log_entry('info', 'STATUS', f"Flag OFF: {flag_name} (no off_effect — stopping)")
                    try:
                        if self.effect_manager:
                            self.effect_manager.stop_all_effects()
                    except Exception as e:
                        print(f"[EventProcessor] ERROR stopping on flag OFF: {e}")
                self.active_status_effects.pop(flag_name, None)

    def _play_status_slot(self, flag_name: str, slot: str, mapping: dict, version: int) -> bool:
        """
        Play the on or off effect for a status flag.
        Returns True if an effect was triggered, False if nothing to play.
        """
        if not self.effect_manager:
            return False

        # v2 inline path
        if version >= 2:
            ve = self._get_status_ve(flag_name, slot)
            if ve:
                print(f"[EventProcessor] Status {slot.upper()}: {flag_name} -> '{ve.name}' (inline)")
                log_entry('info', 'STATUS', f"Flag {slot.upper()}: {flag_name} -> '{ve.name}'")
                try:
                    self.effect_manager.play_visual_effect_object(ve)
                except Exception as e:
                    print(f"[EventProcessor] ERROR status {slot} effect: {e}")
                return True

            # keyboard_default special case
            effect_val = mapping.get(f'{slot}_effect')
            if effect_val == 'keyboard_default':
                print(f"[EventProcessor] Status {slot.upper()}: {flag_name} -> keyboard_default")
                log_entry('info', 'STATUS', f"Flag {slot.upper()}: {flag_name} -> keyboard_default")
                try:
                    self.effect_manager.play_visual_effect('keyboard_default')
                except Exception as e:
                    print(f"[EventProcessor] ERROR status {slot} keyboard_default: {e}")
                return True

            return False  # null slot

        # v1 legacy path: effect_id
        effect_id = mapping.get(f'{slot}_effect_id') if slot == 'on' else mapping.get('off_effect_id')
        if not effect_id:
            return False

        effect_name = effect_id
        try:
            ve = self.effect_manager.visual_library.get_effect(effect_id)
            if ve:
                effect_name = ve.name
        except Exception:
            pass
        print(f"[EventProcessor] Status {slot.upper()}: {flag_name} -> '{effect_name}' ({effect_id})")
        log_entry('info', 'STATUS', f"Flag {slot.upper()}: {flag_name} -> '{effect_name}'")
        try:
            self.effect_manager.play_visual_effect(effect_id)
        except Exception as e:
            print(f"[EventProcessor] ERROR status {slot} effect: {e}")
        return True

    # ── Misc ──────────────────────────────────────────────────────────────────

    def stop_all_effects(self):
        with self.lock:
            self.active_status_effects.clear()
            self._current_priority = 0
            self._priority_expiry = 0.0
            if self.effect_manager:
                self.effect_manager.stop_all_effects()

    def clear_all(self):
        if self.effect_manager:
            self.effect_manager.clear_all()
