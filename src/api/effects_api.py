"""
Effects API - Effect library management.

Provides CRUD operations for visual effects and testing on RGB devices.
"""
import eel
import time
from typing import Optional

# Global references (initialized by init_effects_api)
_library = None
_manager = None
_renderer = None

# Tier 3 connection lost state (persists even after _manager invalidation)
_connection_lost_triggered = False
_connection_lost_devices = []


from api.settings_api import try_ensure_openrgb, with_openrgb_check
from utils.device_keys import device_key_of


def init_effects_api(library, manager):
    """
    Initialize effects API with library and manager instances.

    Args:
        library: VisualEffectLibrary instance
        manager: UnifiedEffectManager instance (can be None if OpenRGB unavailable)
    """
    global _library, _manager, _renderer
    _library = library
    _manager = manager

    # Use the renderer already owned by the manager (which has LED save/restore).
    # Do NOT create a separate VisualEffectRenderer — that would lose the snapshot state.
    if _manager:
        _renderer = _manager.visual_renderer
        print("[OK] Effects API initialized (with hardware support)")
    else:
        _renderer = None
        print("[OK] Effects API initialized (no hardware - effects CRUD only)")


# ========================================
# TIER 3 CONNECTION LOST STATE MANAGEMENT
# ========================================

def set_connection_lost_flag(triggered: bool, devices: list):
    """
    Set Tier 3 connection lost flag (called by renderer).
    This persists even after _manager invalidation.

    Args:
        triggered: Whether modal should be shown
        devices: List of affected device names
    """
    global _connection_lost_triggered, _connection_lost_devices
    from datetime import datetime
    _connection_lost_triggered = triggered
    _connection_lost_devices = devices if devices else []
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] [API] [!] FLAG SET: triggered={triggered}, devices={len(_connection_lost_devices)}")


# ========================================
# EFFECT CRUD OPERATIONS
# ========================================

@eel.expose
def get_effects_list(category: str = None):
    """
    Get effects from library, optionally filtered by category.

    Args:
        category: "event" | "status" | "general" | None (all).
                  When filtering, 'general' effects are always included
                  alongside the requested category.

    Returns:
        dict: { 'success': bool, 'effects': [...], 'count': int }
    """
    try:
        if category:
            # Always include 'general' effects alongside the requested category
            effects = [
                e for e in _library.get_all_effects()
                if e.category in (category, 'general')
            ]
        else:
            effects = _library.get_all_effects()

        return {
            'success': True,
            'effects': [_effect_to_dict(e) for e in effects],
            'count': len(effects)
        }
    except Exception as e:
        print(f"[ERROR] get_effects_list failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def get_effect(effect_id):
    """
    Get single effect by ID.

    Args:
        effect_id: Effect identifier

    Returns:
        dict: {
            'success': bool,
            'effect': effect_dict
        }
    """
    try:
        effect = _library.get_effect(effect_id)

        if not effect:
            return {'success': False, 'error': 'Effect not found'}

        return {
            'success': True,
            'effect': _effect_to_dict(effect)
        }
    except Exception as e:
        print(f"[ERROR] get_effect failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def create_effect(effect_data):
    """
    Create new effect.

    Args:
        effect_data: dict with effect properties

    Returns:
        dict: {'success': bool, 'id': str}
    """
    try:
        effect = _dict_to_effect(effect_data)
        _library.add_effect(effect)
        _library.save_all()
        if _manager:
            _manager.reload_visual_library()

        print(f"[OK] Effect created: {effect.id}")
        return {'success': True, 'id': effect.id}
    except Exception as e:
        print(f"[ERROR] create_effect failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def update_effect(effect_id, effect_data):
    """
    Update existing effect.

    Args:
        effect_id: Effect identifier
        effect_data: dict with updated properties

    Returns:
        dict: {'success': bool}
    """
    try:
        effect = _dict_to_effect(effect_data)
        effect.id = effect_id  # Preserve original ID

        _library.update_effect(effect)
        _library.save_all()
        if _manager:
            _manager.reload_visual_library()

        print(f"[OK] Effect updated: {effect_id}")
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] update_effect failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def delete_effect(effect_id):
    """
    Delete effect from library.

    Args:
        effect_id: Effect identifier

    Returns:
        dict: {'success': bool}
    """
    try:
        from core.visual_effect_library import KEYBOARD_DEFAULT_ID
        if effect_id == KEYBOARD_DEFAULT_ID:
            return {'success': False, 'error': 'Built-in effect cannot be deleted'}

        _library.remove_effect(effect_id)
        _library.save_all()
        if _manager:
            _manager.reload_visual_library()

        print(f"[OK] Effect deleted: {effect_id}")
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] delete_effect failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def duplicate_effect(effect_id):
    """
    Duplicate an existing effect.

    Args:
        effect_id: Effect identifier to duplicate

    Returns:
        dict: {'success': bool, 'id': str}
    """
    try:
        original = _library.get_effect(effect_id)

        if not original:
            return {'success': False, 'error': 'Effect not found'}

        # Create duplicate with new ID and modified name
        duplicate_data = _effect_to_dict(original)
        duplicate_data['name'] = f"{duplicate_data['name']} (Copy)"
        duplicate_data['id'] = f"effect_{int(time.time() * 1000)}"

        duplicate = _dict_to_effect(duplicate_data)
        _library.add_effect(duplicate)
        _library.save_all()
        if _manager:
            _manager.reload_visual_library()

        print(f"[OK] Effect duplicated: {effect_id} -> {duplicate.id}")
        return {'success': True, 'id': duplicate.id}
    except Exception as e:
        print(f"[ERROR] duplicate_effect failed: {e}")
        return {'success': False, 'error': str(e)}


# ========================================
# EFFECT TESTING
# ========================================

@eel.expose
@with_openrgb_check
def test_effect_on_devices(effect_id):
    """
    Test effect on all connected RGB devices.

    Uses the manager's visual_renderer so that LED state is saved before
    the sequence and automatically restored when it finishes.

    Args:
        effect_id: Effect identifier

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        effect = _library.get_effect(effect_id)
        if not effect:
            return {'success': False, 'error': 'Effect not found'}

        # Filter out disabled devices (same as play_visual_effect)
        device_key_func = device_key_of
        active_devices = [d for d in _manager.devices
                         if device_key_func(d) not in _manager.disabled_device_keys]

        # Play on each device using the manager's renderer,
        # which handles LED state save/restore automatically.
        # The renderer will automatically create appropriate fallback effects for each device topology.
        played_on = 0
        for device_ctrl in active_devices:
            try:
                _manager.visual_renderer.start_effect(
                    device_id=device_ctrl.device_id,
                    device_controller=device_ctrl,
                    visual_effect=effect,
                    simulator_mode=False,
                    blocking=False
                )
                played_on += 1
            except Exception as e:
                print(f"[ERROR] Could not start effect on {device_ctrl.topology.device.name}: {e}")

        if played_on == 0:
            return {'success': False, 'error': 'No compatible devices found'}

        print(f"[OK] Effect playing on {played_on} device(s): {effect.name}")
        return {
            'success': True,
            'message': f'Testing effect: {effect.name} ({played_on} device(s))'
        }
    except Exception as e:
        print(f"[ERROR] test_effect_on_devices failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def test_effect_live(effect_data):
    """
    Test the current in-memory effect on all connected RGB devices.

    Does NOT save to library. Converts the raw effect_data dict directly
    to a VisualEffect and plays it, so unsaved changes are reflected.

    Args:
        effect_data: dict with effect properties (same format as create_effect)

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        effect = _dict_to_effect(effect_data)

        # Filter out disabled devices (same as play_visual_effect)
        device_key_func = device_key_of
        active_devices = [d for d in _manager.devices
                         if device_key_func(d) not in _manager.disabled_device_keys]

        played_on = 0
        for device_ctrl in active_devices:
            try:
                _manager.visual_renderer.start_effect(
                    device_id=device_ctrl.device_id,
                    device_controller=device_ctrl,
                    visual_effect=effect,
                    simulator_mode=False,
                    blocking=False
                )
                played_on += 1
            except Exception as e:
                print(f"[ERROR] Could not start live effect on {device_ctrl.topology.device.name}: {e}")

        if played_on == 0:
            return {'success': False, 'error': 'No compatible devices found'}

        print(f"[OK] Live effect playing on {played_on} device(s): {effect.name}")
        return {
            'success': True,
            'message': f'Testing: {effect.name} ({played_on} device(s))'
        }
    except Exception as e:
        print(f"[ERROR] test_effect_live failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def stop_current_effect():
    """
    Stop currently playing effect and restore LED state.

    Returns:
        dict: {'success': bool}
    """
    try:
        # stop_all() stops every device's effect and restores saved LED states
        _manager.visual_renderer.stop_all()
        print("[OK] All effects stopped, LED state restored")
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] stop_current_effect failed: {e}")
        return {'success': False, 'error': str(e)}


# ========================================
# EFFECT METADATA
# ========================================

@eel.expose
def get_effect_types():
    """
    Get available effect types for step creation.

    Returns only implemented BaseEffectType values.

    Returns:
        dict: {
            'success': bool,
            'types': [{value, label, description}, ...]
        }
    """
    return {
        'success': True,
        'types': [
            {
                'value': 'static_transition',
                'label': 'Static Transition',
                'description': 'Smooth transition to a static color'
            },
            {
                'value': 'breath',
                'label': 'Breath',
                'description': 'Breathing effect with fade in/out'
            },
            {
                'value': 'color_cycle',
                'label': 'Color Cycle',
                'description': 'Cycle through multiple colors with direction'
            },
            {
                'value': 'two_color_nuance',
                'label': 'Two Color Nuance',
                'description': 'Gradient transition between two colors across device'
            },
            {
                'value': 'four_corner_nuance',
                'label': 'Four Corner Nuance',
                'description': '2D gradient with four corner colors (keyboards only)'
            },
            {
                'value': 'bloom',
                'label': 'Bloom',
                'description': 'Expanding filled disk fading from center — configurable gradient'
            },
            {
                'value': 'explosion_ring',
                'label': 'Explosion',
                'description': 'True expanding ring with decaying trail — ring color + burn color'
            },
            {
                'value': 'wave',
                'label': 'Wave',
                'description': 'Directional wave propagation with color gradient'
            },
            {
                'value': 'bump',
                'label': 'Bump',
                'description': 'Wave effect with bounce-back at edges'
            },
            {
                'value': 'glitch',
                'label': 'Glitch',
                'description': 'Random LED glitches with persistence and color variation'
            },
            {
                'value': 'fire',
                'label': 'Fire',
                'description': 'Cellular automata fire simulation rising from the bottom (2D only)'
            },
            {
                'value': 'matrix_rain',
                'label': 'Matrix Rain',
                'description': 'Falling columns of glowing characters with fading trail (2D only)'
            },
            {
                'value': 'ocean_waves',
                'label': 'Ocean Waves',
                'description': 'Superimposed sinusoidal waves with 3-zone coloring (2D only)'
            },
            {
                'value': 'plasma',
                'label': 'Plasma',
                'description': 'Weighted sum of 2D sinusoids with HSV palette cycling (2D only)'
            },
            {
                'value': 'aurora',
                'label': 'Aurora',
                'description': 'Vertical light bands with sinusoidal undulation and additive blending (2D only)'
            },
            {
                'value': 'parallax_stars',
                'label': 'Parallax Stars',
                'description': 'Lateral star scroll with 3 depth layers at different speeds (2D only)'
            },
            {
                'value': 'lightning',
                'label': 'Lightning',
                'description': 'Discrete lightning events with flash, jagged bolt and fade (2D only)'
            },
            {
                'value': 'directional_flash',
                'label': 'Directional Flash',
                'description': 'Quarter of the keyboard (hit side) flashes instantly then fades — 2 colors, direction, num flashes (2D only)'
            },
            {
                'value': 'keyboard_default',
                'label': 'Keyboard Mapping',
                'description': 'Restore keyboard to a saved color preset (P1/P2/P3) with soft transition (keyboard only)'
            }
        ]
    }


@eel.expose
def get_post_behaviors():
    """
    Get available post-sequence behaviors.

    Returns:
        dict: {
            'success': bool,
            'behaviors': [{value, label}, ...]
        }
    """
    return {
        'success': True,
        'behaviors': [
            {'value': 'static_color', 'label': 'Static Color'}
        ]
    }


# ========================================
# CONVERSION HELPERS
# ========================================

def _effect_to_dict(effect):
    """
    Convert VisualEffect object to dictionary.

    Args:
        effect: VisualEffect instance

    Returns:
        dict: Effect data
    """
    return {
        'id': effect.id,
        'name': effect.name,
        'description': effect.description,
        'category': getattr(effect, 'category', 'custom'),
        'topology_support': getattr(effect, 'topology_support', ['1D', '2D']),
        'post_behavior': effect.post_behavior.value,
        'post_behavior_data': getattr(effect, 'post_behavior_data', None),
        'metadata': getattr(effect, 'metadata', {}),
        'is_quick_created': getattr(effect, 'is_quick_created', False),  # FIX: Return NEW badge flag
        'created_timestamp': getattr(effect, 'created_timestamp', None),
        'steps': [
            {
                'step_id': s.step_id,
                'effect_type': s.effect_type.value,
                'params': {
                    'colors': s.params.colors,
                    'duration_ms': s.params.duration_ms,
                    'speed': s.params.speed,
                    'direction': s.params.direction,
                    'num_loops': s.params.num_loops,
                    'loop_infinite': s.params.loop_infinite,
                    # Glitch-specific
                    'glitch_percentage': s.params.glitch_percentage,
                    'glitch_duration_ms': s.params.glitch_duration_ms,
                    'duration_variability': s.params.duration_variability,
                    'persistence_percentage': s.params.persistence_percentage,
                    'color_variation': s.params.color_variation,
                    'fade_in_ms': s.params.fade_in_ms,
                    # Natural physics effects
                    'intensity': s.params.intensity,
                    'density': s.params.density,
                    # wave_weights serialized as 4 separate keys so each maps to its own
                    # UI slider (wave_weight_h/v/c/d).  The legacy 'wave_weights' key is
                    # also emitted for backwards compatibility with saved effects.
                    'wave_weights': s.params.wave_weights,
                    'wave_weight_h': s.params.wave_weights[0] if s.params.wave_weights and len(s.params.wave_weights) > 0 else 1.0,
                    'wave_weight_v': s.params.wave_weights[1] if s.params.wave_weights and len(s.params.wave_weights) > 1 else 1.0,
                    'wave_weight_c': s.params.wave_weights[2] if s.params.wave_weights and len(s.params.wave_weights) > 2 else 1.0,
                    'wave_weight_d': s.params.wave_weights[3] if s.params.wave_weights and len(s.params.wave_weights) > 3 else 1.0,
                    'height': s.params.height,
                    'tail_length': s.params.tail_length,
                    'wave_frequency': s.params.wave_frequency,
                    'ripple': s.params.ripple,
                    'bolt_interval_ms': s.params.bolt_interval_ms,
                }
            }
            for s in effect.steps
        ]
    }


def _dict_to_effect(data):
    """
    Convert dictionary to VisualEffect object.

    Args:
        data: dict with effect properties

    Returns:
        VisualEffect: Effect instance
    """
    from core.base_effects import (
        VisualEffect, BaseEffectStep, BaseEffectParams,
        BaseEffectType, PostSequenceBehavior
    )

    # Convert steps
    steps = []
    for i, s in enumerate(data.get('steps', [])):
        p = s['params']
        params = BaseEffectParams(
            colors=[tuple(c) for c in p['colors']],
            duration_ms=p['duration_ms'] or 1000,  # guard: null/0 → 1000ms
            direction=p.get('direction'),
            speed=p.get('speed'),
            num_loops=p.get('num_loops'),
            loop_infinite=p.get('loop_infinite', False),
            # Glitch-specific
            glitch_percentage=p.get('glitch_percentage'),
            glitch_duration_ms=p.get('glitch_duration_ms'),
            duration_variability=p.get('duration_variability'),
            persistence_percentage=p.get('persistence_percentage'),
            color_variation=p.get('color_variation'),
            # Natural physics effects
            intensity=p.get('intensity'),
            density=p.get('density'),
            fade_in_ms=p.get('fade_in_ms', 400 if p.get('fade_in', False) else 0),
            # wave_weights: prefer new individual keys (wave_weight_h/v/c/d) over legacy array.
            # Individual keys are written by the plasma effect UI sliders.
            wave_weights=(
                [p.get('wave_weight_h', 1.0), p.get('wave_weight_v', 1.0),
                 p.get('wave_weight_c', 1.0), p.get('wave_weight_d', 1.0)]
                if 'wave_weight_h' in p
                else p.get('wave_weights')
            ),
            height=p.get('height'),
            tail_length=p.get('tail_length'),
            wave_frequency=p.get('wave_frequency'),
            ripple=p.get('ripple'),
            bolt_interval_ms=p.get('bolt_interval_ms'),
            expansion_factor=p.get('expansion_factor'),
            ring_width=p.get('ring_width'),
            decay_rate=p.get('decay_rate'),
            use_normalized=p.get('use_normalized', False),
        )

        step = BaseEffectStep(
            step_id=s.get('step_id', f"step_{i}"),
            effect_type=BaseEffectType(s['effect_type']),
            params=params
        )
        steps.append(step)

    # Create effect
    # Use 'or' (not dict.get default) so that id=None/null also triggers auto-generation.
    # dict.get('id', default) uses default only when key is absent, not when value is None.
    effect = VisualEffect(
        id=data.get('id') or f"effect_{int(time.time() * 1000)}",
        name=data['name'],
        description=data.get('description', ''),
        steps=steps,
        topology_support=data.get('topology_support', ['1D', '2D']),
        post_behavior=PostSequenceBehavior(data.get('post_behavior', 'static_color')),
        post_behavior_data=data.get('post_behavior_data'),
        category=data.get('category', 'custom'),
        metadata=data.get('metadata', {}),
        is_quick_created=data.get('is_quick_created', False),  # FIX: Preserve NEW badge flag
        created_timestamp=data.get('created_timestamp')
    )

    return effect


# ---------------------------------------------------------------------------
# Tier 3: Connection Lost Modal Status (Polling-Based)
# ---------------------------------------------------------------------------

@eel.expose
def get_connection_lost_status():
    """
    Get current Tier 3 connection lost status (for frontend polling).
    Frontend polls this every 1s to detect when modal should be shown.

    Uses global state that persists even after _manager invalidation.

    Returns:
        dict: {
            'triggered': bool,
            'affected_devices': List[str]
        }
    """
    global _connection_lost_triggered, _connection_lost_devices

    if _connection_lost_triggered:
        print(f"[API] Tier 3 triggered=TRUE! Affected devices: {_connection_lost_devices}")

    return {
        'triggered': _connection_lost_triggered,
        'affected_devices': _connection_lost_devices
    }


@eel.expose
def clear_connection_lost_status():
    """
    Clear Tier 3 connection lost flag (called after modal is shown/closed).

    Returns:
        dict: {'success': bool}
    """
    global _connection_lost_triggered, _connection_lost_devices

    _connection_lost_triggered = False
    _connection_lost_devices = []

    print("[API] Cleared connection lost status flag")
    return {'success': True}
