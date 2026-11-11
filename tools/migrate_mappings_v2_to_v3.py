"""
Migrazione event_mappings.json v2 -> v3.

Risolve ogni effect_id in visual_effects.json e incorpora la definizione
inline. Il campo 'id', 'is_quick_created', 'created_timestamp' vengono rimossi
dal dict copiato (generati a runtime).

Salva backup .v2.bak.json prima di sovrascrivere.
"""
import json
import sys
from pathlib import Path

MAPPINGS_FILE = Path("config/event_mappings.json")
EFFECTS_FILE  = Path("config/visual_effects.json")

_STRIP_FIELDS = {"id", "is_quick_created", "created_timestamp"}


def main():
    if not MAPPINGS_FILE.exists():
        print(f"[ERROR] {MAPPINGS_FILE} not found")
        sys.exit(1)
    if not EFFECTS_FILE.exists():
        print(f"[ERROR] {EFFECTS_FILE} not found")
        sys.exit(1)

    mappings_data = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
    effects_data  = json.loads(EFFECTS_FILE.read_text(encoding="utf-8"))

    version = mappings_data.get("version", 2)
    if version == 3:
        print("[INFO] Already v3, nothing to do.")
        return

    if version != 2:
        print(f"[ERROR] Expected version 2, got {version}")
        sys.exit(1)

    # Build effects lookup: id -> effect dict
    effects_by_id = {e["id"]: e for e in effects_data.get("effects", [])}

    new_mappings = {}
    skipped = []

    for event_name, mapping in mappings_data.get("mappings", {}).items():
        effect_id = mapping.get("effect_id", "")

        if effect_id == "keyboard_default":
            inline_effect = "keyboard_default"
        elif effect_id and effect_id in effects_by_id:
            raw = {k: v for k, v in effects_by_id[effect_id].items()
                   if k not in _STRIP_FIELDS}
            inline_effect = raw
        else:
            if effect_id:
                skipped.append((event_name, effect_id))
            inline_effect = None

        new_mappings[event_name] = {
            "priority": mapping.get("priority", 5),
            "enabled":  mapping.get("enabled", True),
            "effect":   inline_effect,
        }

    # Backup
    backup = MAPPINGS_FILE.with_suffix(".v2.bak.json")
    backup.write_text(MAPPINGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[OK] Backup saved to {backup}")

    # Write v3
    output = {"version": 3, "mappings": new_mappings}
    MAPPINGS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[OK] Migrated {len(new_mappings)} mappings to v3")
    if skipped:
        print(f"[WARN] {len(skipped)} effect_id(s) not found in library (set to null):")
        for ev, eid in skipped:
            print(f"       {ev}: {eid!r}")


if __name__ == "__main__":
    main()
