"""
Profiles API - Export and import of complete configuration profiles.

Allows saving and loading effects + event mappings as a single JSON file
for personal backups or sharing configurations with other users.
"""
import eel
from datetime import datetime

# Global references (initialized by init_profiles_api)
_visual_library = None
_event_processor = None


def init_profiles_api(visual_library, event_processor):
    """
    Initialize profiles API with library and processor instances.

    Args:
        visual_library: VisualEffectLibrary instance
        event_processor: EventProcessor instance
    """
    global _visual_library, _event_processor
    _visual_library = visual_library
    _event_processor = event_processor
    print("[OK] Profiles API initialized")


@eel.expose
def export_profile():
    """
    Return the full profile (effects + mappings) as a dict.

    Returns:
        dict: {
            'success': bool,
            'profile': {version, app, exported_at, effects, mappings}
        }
    """
    try:
        effects_data = {
            "version": 1,
            "effects": [e.to_dict() for e in _visual_library.effects.values()]
        }
        mappings_data = {
            "version": 2,
            "mappings": _event_processor.mappings
        }
        profile = {
            "version": 1,
            "app": "ED:Event2Led",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "effects": effects_data,
            "mappings": mappings_data
        }
        print(f"[OK] Profile exported: {len(_visual_library.effects)} effects, "
              f"{len(_event_processor.mappings)} mappings")
        return {"success": True, "profile": profile}
    except Exception as e:
        print(f"[ERROR] export_profile failed: {e}")
        return {"success": False, "error": str(e)}


@eel.expose
def import_profile(profile_data):
    """
    Replace total: overwrite effects and mappings from profile JSON.

    Args:
        profile_data: dict with profile structure {effects, mappings}

    Returns:
        dict: {
            'success': bool,
            'effects_count': int,
            'mappings_count': int
        }
    """
    try:
        if "effects" not in profile_data or "mappings" not in profile_data:
            return {"success": False, "error": "Invalid profile format"}

        # --- Replace effects ---
        from core.base_effects import VisualEffect
        _visual_library.effects.clear()
        for effect_dict in profile_data["effects"].get("effects", []):
            effect = VisualEffect.from_dict(effect_dict)
            _visual_library.effects[effect.id] = effect
        _visual_library.save_all()

        # --- Replace mappings ---
        _event_processor.mappings = profile_data["mappings"].get("mappings", {})
        _event_processor.save_mappings()

        print(f"[OK] Profile imported: {len(_visual_library.effects)} effects, "
              f"{len(_event_processor.mappings)} mappings")
        return {
            "success": True,
            "effects_count": len(_visual_library.effects),
            "mappings_count": len(_event_processor.mappings)
        }
    except Exception as e:
        print(f"[ERROR] import_profile failed: {e}")
        return {"success": False, "error": str(e)}
