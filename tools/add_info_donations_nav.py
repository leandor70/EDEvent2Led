"""
add_info_donations_nav.py
Adds "info_donations" key to navigation section in DE, ES, FR i18n files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

TRANSLATIONS = {
    "de": "Info & Spenden",
    "es": "Info y Donaciones",
    "fr": "Info et Dons"
}

def update_file(lang_code: str):
    """Add info_donations key to navigation section."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add info_donations key to navigation section
    if 'navigation' in data:
        # Insert after system_status, before core_online
        nav = data['navigation']
        keys = list(nav.keys())

        # Find index of core_online
        try:
            idx = keys.index('core_online')
            # Create new dict with key inserted at the right position
            new_nav = {}
            for i, key in enumerate(keys):
                new_nav[key] = nav[key]
                if key == 'system_status':
                    new_nav['info_donations'] = TRANSLATIONS[lang_code]
            data['navigation'] = new_nav
            print(f"  [OK] Added navigation.info_donations = \"{TRANSLATIONS[lang_code]}\"")
        except ValueError:
            # core_online not found, just append
            nav['info_donations'] = TRANSLATIONS[lang_code]
            print(f"  [OK] Appended navigation.info_donations = \"{TRANSLATIONS[lang_code]}\"")
    else:
        print(f"  [SKIP] navigation section not found")
        return

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Add info_donations to DE, ES, FR navigation sections."""
    print("="*70)
    print("  Adding Info & Donations Navigation Key (DE, ES, FR)")
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
