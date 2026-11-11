"""
add_disclaimer_p3.py
Adds disclaimer_p3 (photosensitivity warning) to DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DISCLAIMER_P3 = {
    "de": "WARNUNG: Blinkende Lichter und dynamische visuelle Reize können bei empfindlichen Personen körperliche Reaktionen oder epileptische Anfälle auslösen.",
    "es": "ADVERTENCIA: Las luces intermitentes y los estímulos visuales dinámicos pueden desencadenar reacciones físicas o crisis epilépticas en individuos susceptibles.",
    "fr": "AVERTISSEMENT: Les lumières clignotantes et les stimuli visuels dynamiques peuvent déclencher des réactions physiques ou des crises d'épilepsie chez les personnes sensibles."
}

def update_file(lang_code: str):
    """Add disclaimer_p3 to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add disclaimer_p3 to about section
    if 'about' in data:
        data['about']['disclaimer_p3'] = DISCLAIMER_P3[lang_code]
        print(f"  [OK] Added disclaimer_p3 to about section")
    else:
        print(f"  [WARN] 'about' section not found in {lang_code}.json")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Add disclaimer_p3 (photosensitivity warning) to DE, ES, FR."""
    print("="*70)
    print("  Adding Disclaimer P3 (Photosensitivity Warning)")
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
