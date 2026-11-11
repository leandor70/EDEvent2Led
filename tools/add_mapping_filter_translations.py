"""
Add mapping filter translations for Events page to i18n JSON files.
"""

import json
from pathlib import Path

# Define new translations for mapping filter
NEW_TRANSLATIONS = {
    "sections.event_mapping.filter_label": {
        "en": "Filter:",
        "it": "Filtro:",
        "de": "Filter:",
        "es": "Filtro:",
        "fr": "Filtre:"
    },
    "sections.event_mapping.filter_all": {
        "en": "All",
        "it": "Tutti",
        "de": "Alle",
        "es": "Todos",
        "fr": "Tous"
    },
    "sections.event_mapping.filter_mapped": {
        "en": "Mapped",
        "it": "Mappati",
        "de": "Zugeordnet",
        "es": "Mapeados",
        "fr": "Mappés"
    },
    "sections.event_mapping.filter_unmapped": {
        "en": "Unmapped",
        "it": "Non Mappati",
        "de": "Nicht zugeordnet",
        "es": "Sin mapear",
        "fr": "Non mappés"
    }
}

def update_i18n_files():
    """Add missing translations to all i18n JSON files."""
    i18n_dir = Path(__file__).parent.parent / "web" / "config" / "i18n"
    languages = ["en", "it", "de", "es", "fr"]

    for lang in languages:
        file_path = i18n_dir / f"{lang}.json"
        print(f"[OK] Processing {file_path.name}...")

        # Read existing JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ensure sections.event_mapping exists
        if "sections" not in data:
            data["sections"] = {}
        if "event_mapping" not in data["sections"]:
            data["sections"]["event_mapping"] = {}

        # Add missing translations
        added_count = 0
        for key, translations in NEW_TRANSLATIONS.items():
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
    print("  Add Mapping Filter Translations")
    print("=" * 70)
    print()

    update_i18n_files()

    print("=" * 70)
    print("  ALL FILES UPDATED")
    print("=" * 70)
    print()
    print("Next step: Reload Events page to see 3-way mapping filter")
