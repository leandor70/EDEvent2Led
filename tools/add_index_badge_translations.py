"""
Add missing badge translations for index.html to i18n JSON files.
"""

import json
from pathlib import Path

# Define new badge translations
NEW_BADGE_TRANSLATIONS = {
    "badges.table": {
        "en": "Table",
        "it": "Tabella",
        "de": "Tabelle",
        "es": "Tabla",
        "fr": "Tableau"
    },
    "badges.core": {
        "en": "Core",
        "it": "Core",
        "de": "Kern",
        "es": "Núcleo",
        "fr": "Noyau"
    },
    "badges.visual": {
        "en": "Visual",
        "it": "Visuale",
        "de": "Visuell",
        "es": "Visual",
        "fr": "Visuel"
    },
    "badges.advanced": {
        "en": "Advanced",
        "it": "Avanzato",
        "de": "Erweitert",
        "es": "Avanzado",
        "fr": "Avancé"
    },
    "badges.live": {
        "en": "Live",
        "it": "Live",
        "de": "Live",
        "es": "En Vivo",
        "fr": "Direct"
    },
    "badges.flags": {
        "en": "Flags",
        "it": "Flag",
        "de": "Flags",
        "es": "Indicadores",
        "fr": "Drapeaux"
    }
}

def update_i18n_files():
    """Add missing badge translations to all i18n JSON files."""
    i18n_dir = Path(__file__).parent.parent / "web" / "config" / "i18n"
    languages = ["en", "it", "de", "es", "fr"]

    for lang in languages:
        file_path = i18n_dir / f"{lang}.json"
        print(f"[OK] Processing {file_path.name}...")

        # Read existing JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ensure badges section exists
        if "badges" not in data:
            data["badges"] = {}

        # Add missing translations
        added_count = 0
        for key, translations in NEW_BADGE_TRANSLATIONS.items():
            parts = key.split('.')
            if len(parts) == 2:
                section, item = parts
                if item not in data[section]:
                    data[section][item] = translations[lang]
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
    print("  Add Index Badge Translations")
    print("=" * 70)
    print()

    update_i18n_files()

    print("=" * 70)
    print("  ALL FILES UPDATED")
    print("=" * 70)
    print()
    print("Next step: Reload the application to see translated badge texts")
