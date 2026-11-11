"""
update_devices_i18n.py
Adds devices page missing keys to DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DEVICE_TESTING_KEYS = {
    "de": {
        "effect_preview_title": "Effekt-Vorschau",
        "effect_preview_description": "Testen Sie Ihre Bibliothekseffekte auf echter Hardware",
        "effect_preview_info": "Die Vorschau führt die vollständige Effektsequenz auf allen verbundenen Geräten aus. Erstellen und bearbeiten Sie Effekte im Effekt-Editor.",
        "select_mode_placeholder": "-- Modus wählen --"
    },
    "es": {
        "effect_preview_title": "Vista Previa de Efecto",
        "effect_preview_description": "Prueba los efectos de tu biblioteca en hardware real",
        "effect_preview_info": "La vista previa ejecuta la secuencia completa del efecto en todos los dispositivos conectados. Crea y edita efectos en el Editor de Efectos.",
        "select_mode_placeholder": "-- Seleccionar Modo --"
    },
    "fr": {
        "effect_preview_title": "Aperçu de l'Effet",
        "effect_preview_description": "Testez les effets de votre bibliothèque sur du matériel réel",
        "effect_preview_info": "L'aperçu exécute la séquence complète de l'effet sur tous les appareils connectés. Créez et modifiez des effets dans l'Éditeur d'Effets.",
        "select_mode_placeholder": "-- Sélectionner Mode --"
    }
}

COMMON_LOADING_EFFECTS = {
    "de": "Effekte werden geladen...",
    "es": "Cargando efectos...",
    "fr": "Chargement des effets..."
}

def update_file(lang_code: str):
    """Add devices page keys to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add 4 keys to sections.device_testing
    if 'sections' in data and 'device_testing' in data['sections']:
        for key, value in DEVICE_TESTING_KEYS[lang_code].items():
            data['sections']['device_testing'][key] = value
        print(f"  [OK] Added 4 keys to sections.device_testing")

    # Add loading_effects to common
    if 'common' in data:
        # Find position of loading_logs key and insert after it
        common_keys = list(data['common'].keys())
        if 'loading_logs' in common_keys:
            idx = common_keys.index('loading_logs') + 1
            # Rebuild dict with loading_effects inserted
            new_common = {}
            for i, k in enumerate(common_keys):
                new_common[k] = data['common'][k]
                if i == idx - 1:
                    new_common['loading_effects'] = COMMON_LOADING_EFFECTS[lang_code]
            data['common'] = new_common
        else:
            # Fallback: add at end
            data['common']['loading_effects'] = COMMON_LOADING_EFFECTS[lang_code]
        print(f"  [OK] Added loading_effects to common")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Update devices page keys in DE, ES, FR."""
    print("="*70)
    print("  Updating Devices Page (DE, ES, FR)")
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
