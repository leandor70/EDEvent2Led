"""
Fix missing i18n translations in HTML files and JSON i18n files.
This script adds data-i18n attributes and corresponding translations.
"""

import json
from pathlib import Path

# Define missing translations
MISSING_TRANSLATIONS = {
    # Events page - category filters
    "categories.all": {
        "en": "All",
        "it": "Tutto",
        "de": "Alle",
        "es": "Todo",
        "fr": "Tout"
    },
    "categories.startup": {
        "en": "Startup",
        "it": "Avvio",
        "de": "Start",
        "es": "Inicio",
        "fr": "Démarrage"
    },
    "categories.travel": {
        "en": "Travel",
        "it": "Viaggio",
        "de": "Reisen",
        "es": "Viaje",
        "fr": "Voyage"
    },
    "categories.combat": {
        "en": "Combat",
        "it": "Combattimento",
        "de": "Kampf",
        "es": "Combate",
        "fr": "Combat"
    },
    "categories.exploration": {
        "en": "Exploration",
        "it": "Esplorazione",
        "de": "Erkundung",
        "es": "Exploración",
        "fr": "Exploration"
    },
    "categories.trade": {
        "en": "Trade",
        "it": "Commercio",
        "de": "Handel",
        "es": "Comercio",
        "fr": "Commerce"
    },
    "categories.station": {
        "en": "Station",
        "it": "Stazione",
        "de": "Station",
        "es": "Estación",
        "fr": "Station"
    },
    "categories.powerplay": {
        "en": "Powerplay",
        "it": "Powerplay",
        "de": "Powerplay",
        "es": "Powerplay",
        "fr": "Powerplay"
    },
    "categories.squadrons": {
        "en": "Squadrons",
        "it": "Squadroni",
        "de": "Geschwader",
        "es": "Escuadrones",
        "fr": "Escadrons"
    },
    "categories.fleet": {
        "en": "Fleet",
        "it": "Flotta",
        "de": "Flotte",
        "es": "Flota",
        "fr": "Flotte"
    },
    "categories.odyssey": {
        "en": "Odyssey",
        "it": "Odyssey",
        "de": "Odyssey",
        "es": "Odyssey",
        "fr": "Odyssey"
    },
    "categories.other": {
        "en": "Other",
        "it": "Altro",
        "de": "Andere",
        "es": "Otro",
        "fr": "Autre"
    },
    # Buttons
    "buttons.revert": {
        "en": "REVERT",
        "it": "RIPRISTINA",
        "de": "ZURÜCKSETZEN",
        "es": "REVERTIR",
        "fr": "RÉTABLIR"
    },
    "buttons.deassign": {
        "en": "DEASSIGN",
        "it": "RIMUOVI",
        "de": "ENTFERNEN",
        "es": "DESASIGNAR",
        "fr": "DÉSASSIGNER"
    },
    # Index page badges
    "badges.base": {
        "en": "Base",
        "it": "Base",
        "de": "Basis",
        "es": "Base",
        "fr": "Base"
    },
    "badges.forms": {
        "en": "Forms",
        "it": "Moduli",
        "de": "Formulare",
        "es": "Formularios",
        "fr": "Formulaires"
    },
    "badges.hardware": {
        "en": "Hardware",
        "it": "Hardware",
        "de": "Hardware",
        "es": "Hardware",
        "fr": "Matériel"
    },
    "badges.devices": {
        "en": "Devices",
        "it": "Dispositivi",
        "de": "Geräte",
        "es": "Dispositivos",
        "fr": "Appareils"
    },
    "badges.editor": {
        "en": "Editor",
        "it": "Editor",
        "de": "Editor",
        "es": "Editor",
        "fr": "Éditeur"
    },
    "badges.complex": {
        "en": "Complex",
        "it": "Complesso",
        "de": "Komplex",
        "es": "Complejo",
        "fr": "Complexe"
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

        # Ensure top-level keys exist
        if "categories" not in data:
            data["categories"] = {}
        if "badges" not in data:
            data["badges"] = {}

        # Add missing translations
        added_count = 0
        for key, translations in MISSING_TRANSLATIONS.items():
            parts = key.split('.')
            if len(parts) == 2:
                section, item = parts
                if item not in data[section]:
                    data[section][item] = translations[lang]
                    added_count += 1
                    print(f"  + Added {key}: {translations[lang]}")

        # Write back with proper formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] {file_path.name}: {added_count} translations added\n")

if __name__ == "__main__":
    print("=" * 70)
    print("  Fix Missing i18n Translations")
    print("=" * 70)
    print()

    update_i18n_files()

    print("=" * 70)
    print("  ALL FILES UPDATED")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Update HTML files to add data-i18n attributes")
    print("2. Test the application to verify translations appear correctly")
