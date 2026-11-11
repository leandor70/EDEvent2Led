"""
Add NEW filter button translation for Effects Library to i18n JSON files.
"""

import json
from pathlib import Path

# Define new translation for NEW filter button
NEW_FILTER_TRANSLATION = {
    "sections.effects_library.filter_new": {
        "en": "NEW",
        "it": "NUOVO",
        "de": "NEU",
        "es": "NUEVO",
        "fr": "NOUVEAU"
    }
}

def update_i18n_files():
    """Add missing NEW filter translation to all i18n JSON files."""
    i18n_dir = Path(__file__).parent.parent / "web" / "config" / "i18n"
    languages = ["en", "it", "de", "es", "fr"]

    for lang in languages:
        file_path = i18n_dir / f"{lang}.json"
        print(f"[OK] Processing {file_path.name}...")

        # Read existing JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ensure sections.effects_library exists
        if "sections" not in data:
            data["sections"] = {}
        if "effects_library" not in data["sections"]:
            data["sections"]["effects_library"] = {}

        # Add missing translation
        added_count = 0
        for key, translations in NEW_FILTER_TRANSLATION.items():
            parts = key.split('.')
            if len(parts) == 3:
                section1, section2, item = parts
                if item not in data[section1][section2]:
                    data[section1][section2][item] = translations[lang]
                    added_count += 1
                    print(f"  + Added {key}: {translations[lang]}")
                else:
                    print(f"  - Skipped {key} (already exists)")

        # Write back with proper formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] {file_path.name}: {added_count} translations added\n")

if __name__ == "__main__":
    print("=" * 70)
    print("  Add NEW Filter Button Translations")
    print("=" * 70)
    print()

    update_i18n_files()

    print("=" * 70)
    print("  ALL FILES UPDATED")
    print("=" * 70)
    print()
    print("Next step: Reload Effects Editor to see NEW filter toggle button")
