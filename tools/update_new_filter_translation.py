"""
Update NEW filter translation from button to toggle label.
Changes "NEW" to "Show NEW" for clearer UI affordance.
"""

import json
from pathlib import Path

# Updated translations for toggle label
SHOW_NEW_TRANSLATIONS = {
    "en": "Show NEW",
    "it": "Mostra NUOVI",
    "de": "NEUE anzeigen",
    "es": "Mostrar NUEVOS",
    "fr": "Afficher NOUVEAUX"
}

def update_i18n_files():
    """Update show_new translation in all i18n JSON files."""
    i18n_dir = Path(__file__).parent.parent / "web" / "config" / "i18n"
    languages = ["en", "it", "de", "es", "fr"]

    for lang in languages:
        file_path = i18n_dir / f"{lang}.json"
        print(f"[OK] Processing {file_path.name}...")

        # Read existing JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Update filter_new → show_new
        if "sections" in data and "effects_library" in data["sections"]:
            # Remove old key if exists
            if "filter_new" in data["sections"]["effects_library"]:
                del data["sections"]["effects_library"]["filter_new"]
                print(f"  - Removed old key: filter_new")

            # Add new key
            data["sections"]["effects_library"]["show_new"] = SHOW_NEW_TRANSLATIONS[lang]
            print(f"  + Added show_new: {SHOW_NEW_TRANSLATIONS[lang]}")

        # Write back with proper formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] {file_path.name}: Updated\n")

if __name__ == "__main__":
    print("=" * 70)
    print("  Update NEW Filter Translation (Button -> Toggle)")
    print("=" * 70)
    print()

    update_i18n_files()

    print("=" * 70)
    print("  ALL FILES UPDATED")
    print("=" * 70)
    print()
    print("Next step: Reload Effects Editor to see toggle switch")
