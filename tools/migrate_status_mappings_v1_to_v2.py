"""
Migrazione status_mappings.json v1 -> v2.

Risolve on_effect_id / off_effect_id in visual_effects.json e incorpora
le definizioni inline come on_effect / off_effect.

Salva backup .v1.bak.json prima di sovrascrivere.
"""
import json
import sys
from pathlib import Path

MAPPINGS_FILE = Path("config/status_mappings.json")
EFFECTS_FILE  = Path("config/visual_effects.json")

_STRIP_FIELDS = {"id", "is_quick_created", "created_timestamp"}


def _resolve(effect_id, effects_by_id):
    """Resolve an effect_id to an inline dict, 'keyboard_default', or None."""
    if not effect_id:
        return None
    if effect_id == "keyboard_default":
        return "keyboard_default"
    if effect_id in effects_by_id:
        return {k: v for k, v in effects_by_id[effect_id].items()
                if k not in _STRIP_FIELDS}
    return None


def main():
    if not MAPPINGS_FILE.exists():
        print(f"[ERROR] {MAPPINGS_FILE} not found")
        sys.exit(1)
    if not EFFECTS_FILE.exists():
        print(f"[ERROR] {EFFECTS_FILE} not found")
        sys.exit(1)

    mappings_data = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
    effects_data  = json.loads(EFFECTS_FILE.read_text(encoding="utf-8"))

    version = mappings_data.get("version", 1)
    if version == 2:
        print("[INFO] Already v2, nothing to do.")
        return

    effects_by_id = {e["id"]: e for e in effects_data.get("effects", [])}

    new_mappings = {}
    skipped = []

    for flag_name, mapping in mappings_data.get("mappings", {}).items():
        on_id  = mapping.get("on_effect_id")
        off_id = mapping.get("off_effect_id")

        on_effect  = _resolve(on_id,  effects_by_id)
        off_effect = _resolve(off_id, effects_by_id)

        if on_id and on_effect is None:
            skipped.append((flag_name, "on",  on_id))
        if off_id and off_effect is None:
            skipped.append((flag_name, "off", off_id))

        new_mappings[flag_name] = {
            "enabled":    mapping.get("enabled", True),
            "on_effect":  on_effect,
            "off_effect": off_effect,
        }

    # Backup
    backup = MAPPINGS_FILE.with_suffix(".v1.bak.json")
    backup.write_text(MAPPINGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[OK] Backup saved to {backup}")

    output = {"version": 2, "mappings": new_mappings}
    MAPPINGS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[OK] Migrated {len(new_mappings)} status mappings to v2")
    if skipped:
        print(f"[WARN] {len(skipped)} effect_id(s) not found (set to null):")
        for flag, slot, eid in skipped:
            print(f"       {flag}.{slot}: {eid!r}")


if __name__ == "__main__":
    main()
