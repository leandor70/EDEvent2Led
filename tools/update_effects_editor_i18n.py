"""
update_effects_editor_i18n.py
Adds effects-editor page missing keys to DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

EFFECTS_LIBRARY_KEYS = {
    "de": {
        "cat_all": "Alle",
        "cat_events": "Ereignisse",
        "cat_status": "Status",
        "cat_general": "Allgemein"
    },
    "es": {
        "cat_all": "Todos",
        "cat_events": "Eventos",
        "cat_status": "Estado",
        "cat_general": "General"
    },
    "fr": {
        "cat_all": "Tous",
        "cat_events": "Événements",
        "cat_status": "Statut",
        "cat_general": "Général"
    }
}

EFFECT_EDITOR_KEYS = {
    "de": {
        "effect_name_placeholder": "Effektname",
        "category_label": "Kategorie:",
        "cat_event": "Ereignis",
        "cat_status": "Status",
        "cat_general": "Allgemein",
        "select_effect_hint": "Wählen Sie einen Effekt zum Bearbeiten"
    },
    "es": {
        "effect_name_placeholder": "Nombre del Efecto",
        "category_label": "Categoría:",
        "cat_event": "Evento",
        "cat_status": "Estado",
        "cat_general": "General",
        "select_effect_hint": "Selecciona un efecto para empezar a editar"
    },
    "fr": {
        "effect_name_placeholder": "Nom de l'Effet",
        "category_label": "Catégorie:",
        "cat_event": "Événement",
        "cat_status": "Statut",
        "cat_general": "Général",
        "select_effect_hint": "Sélectionnez un effet pour commencer à éditer"
    }
}

TOOLTIPS_CLONE_DISABLED = {
    "de": "Wählen Sie einen Effekt zum Klonen",
    "es": "Selecciona un efecto para clonar",
    "fr": "Sélectionnez un effet à cloner"
}

def update_file(lang_code: str):
    """Add effects-editor page keys to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add 4 keys to sections.effects_library
    if 'sections' in data and 'effects_library' in data['sections']:
        for key, value in EFFECTS_LIBRARY_KEYS[lang_code].items():
            data['sections']['effects_library'][key] = value
        print(f"  [OK] Added 4 keys to sections.effects_library")

    # Add 6 keys to sections.effect_editor
    if 'sections' in data and 'effect_editor' in data['sections']:
        for key, value in EFFECT_EDITOR_KEYS[lang_code].items():
            data['sections']['effect_editor'][key] = value
        print(f"  [OK] Added 6 keys to sections.effect_editor")

    # Add clone_effect_disabled to tooltips
    if 'tooltips' in data:
        data['tooltips']['clone_effect_disabled'] = TOOLTIPS_CLONE_DISABLED[lang_code]
        print(f"  [OK] Added clone_effect_disabled to tooltips")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Update effects-editor page keys in DE, ES, FR."""
    print("="*70)
    print("  Updating Effects Editor Page (DE, ES, FR)")
    print("="*70)

    for lang_code in ['de', 'es', 'fr']:
        try:
            update_file(lang_code)
        except Exception as e:
            print(f"  [FAIL] Error updating {lang_code}.json: {e}")

    print("\n" + "="*70)
    print("  DONE! All translation files updated.")
    print("="*70)

if __name__ == '__main__':
    main()
