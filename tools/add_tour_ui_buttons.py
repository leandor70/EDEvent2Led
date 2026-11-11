"""
add_tour_ui_buttons.py
Adds show_guide (navigation) and reset_guides buttons (buttons) to IT, DE, ES, FR
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

NAVIGATION_SHOW_GUIDE = {
    "it": "Mostra Guida",
    "de": "Anleitung Anzeigen",
    "es": "Mostrar Guía",
    "fr": "Afficher le Guide"
}

BUTTONS_RESET_GUIDES = {
    "it": {
        "reset_guides": "Resetta Tutte le Guide",
        "reset_guides_confirm": "Resettare tutte le guide contestuali? Verranno mostrate di nuovo quando visiterai ogni pagina.",
        "reset_guides_success": "Tutte le guide sono state resettate!"
    },
    "de": {
        "reset_guides": "Alle Anleitungen Zurücksetzen",
        "reset_guides_confirm": "Alle kontextbezogenen Anleitungen zurücksetzen? Sie werden erneut angezeigt, wenn Sie jede Seite besuchen.",
        "reset_guides_success": "Alle Anleitungen wurden zurückgesetzt!"
    },
    "es": {
        "reset_guides": "Restablecer Todas las Guías",
        "reset_guides_confirm": "¿Restablecer todas las guías contextuales? Se mostrarán de nuevo cuando visites cada página.",
        "reset_guides_success": "¡Todas las guías han sido restablecidas!"
    },
    "fr": {
        "reset_guides": "Réinitialiser Tous les Guides",
        "reset_guides_confirm": "Réinitialiser tous les guides contextuels ? Ils seront à nouveau affichés lorsque vous visiterez chaque page.",
        "reset_guides_success": "Tous les guides ont été réinitialisés!"
    }
}

def update_file(lang_code: str):
    """Add show_guide and reset_guides keys."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add show_guide to navigation
    if 'navigation' in data:
        data['navigation']['show_guide'] = NAVIGATION_SHOW_GUIDE[lang_code]
        print(f"  [OK] Added navigation.show_guide")
    else:
        print(f"  [WARN] navigation section not found")

    # Add reset_guides keys to buttons
    if 'buttons' in data:
        for key, value in BUTTONS_RESET_GUIDES[lang_code].items():
            data['buttons'][key] = value
        print(f"  [OK] Added 3 keys to buttons section")
    else:
        print(f"  [WARN] buttons section not found")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Add tour UI buttons to IT, DE, ES, FR."""
    print("="*70)
    print("  Adding Tour UI Buttons (IT, DE, ES, FR)")
    print("="*70)

    for lang_code in ['it', 'de', 'es', 'fr']:
        try:
            update_file(lang_code)
        except Exception as e:
            print(f"  [FAIL] Error updating {lang_code}.json: {e}")

    print("\n" + "="*70)
    print("  DONE! All translation files updated.")
    print("="*70)

if __name__ == '__main__':
    main()
