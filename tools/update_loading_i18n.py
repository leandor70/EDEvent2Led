"""
update_loading_i18n.py
Adds loading.error key to DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

LOADING_ERROR = {
    "de": "Initialisierungsfehler",
    "es": "Error de inicializacion",
    "fr": "Erreur d'initialisation"
}

def update_file(lang_code: str):
    """Add loading.error to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add error key to pages.loading
    if 'pages' in data and 'loading' in data['pages']:
        data['pages']['loading']['error'] = LOADING_ERROR[lang_code]
        print(f"  [OK] Added loading.error")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Add loading.error to DE, ES, FR."""
    print("="*70)
    print("  Updating Loading Page (DE, ES, FR)")
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
