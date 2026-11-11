"""
update_pages_section.py
Updates pages section in ES and FR (DE already done manually)
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

PAGES_SECTIONS = {
    "es": {
        "home": {
            "title": "Control de Iluminación RGB para Elite Dangerous",
            "subtitle": "Monitoreo de Journal en Tiempo Real · Integración OpenRGB · Secuenciador de Efectos Multi-Paso",
            "page_title": "ED:Event2Led",
            "journal_monitor_title": "Monitor de Journal",
            "last_event_title": "Último Evento",
            "no_effect_yet": "Ningún efecto activado aún",
            "checking": "Verificando...",
            "inactive": "Inactivo"
        },
        "configuration": {
            "page_title": "ED:Event2Led Configuración"
        },
        "effects_editor": {
            "page_title": "ED:Event2Led Editor de Efectos"
        },
        "events": {
            "page_title": "ED:Event2Led Mapeo de Eventos"
        },
        "device_testing": {
            "page_title": "ED:Event2Led Gestión de Dispositivos"
        },
        "activity_logs": {
            "page_title": "ED:Event2Led Registros de Actividad"
        },
        "keyboard_designer": {
            "page_title": "ED:Event2Led Diseñador de Teclado"
        },
        "status": {
            "title": "ESTADO DEL JUEGO",
            "subtitle": "Banderas de Nave y Odyssey en Tiempo Real",
            "page_title": "ED:Event2Led - Estado del Juego"
        },
        "loading": {
            "page_title": "ED:Event2Led - Cargando",
            "initializing": "Inicializando sistema..."
        }
    },
    "fr": {
        "home": {
            "title": "Contrôle d'Éclairage RGB pour Elite Dangerous",
            "subtitle": "Surveillance de Journal en Temps Réel · Intégration OpenRGB · Séquenceur d'Effets Multi-Étapes",
            "page_title": "ED:Event2Led",
            "journal_monitor_title": "Moniteur de Journal",
            "last_event_title": "Dernier Événement",
            "no_effect_yet": "Aucun effet déclenché encore",
            "checking": "Vérification...",
            "inactive": "Inactif"
        },
        "configuration": {
            "page_title": "ED:Event2Led Configuration"
        },
        "effects_editor": {
            "page_title": "ED:Event2Led Éditeur d'Effets"
        },
        "events": {
            "page_title": "ED:Event2Led Mappage d'Événements"
        },
        "device_testing": {
            "page_title": "ED:Event2Led Gestion des Appareils"
        },
        "activity_logs": {
            "page_title": "ED:Event2Led Journaux d'Activité"
        },
        "keyboard_designer": {
            "page_title": "ED:Event2Led Concepteur de Clavier"
        },
        "status": {
            "title": "ÉTAT DU JEU",
            "subtitle": "Drapeaux du Vaisseau et d'Odyssey en Temps Réel",
            "page_title": "ED:Event2Led - État du Jeu"
        },
        "loading": {
            "page_title": "ED:Event2Led - Chargement",
            "initializing": "Initialisation du système..."
        }
    }
}

def update_pages(lang_code: str):
    """Update pages section with missing keys."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating pages section in {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Merge pages section
    if 'pages' in data and lang_code in PAGES_SECTIONS:
        for page_key, page_data in PAGES_SECTIONS[lang_code].items():
            if page_key not in data['pages']:
                # Add new page
                data['pages'][page_key] = page_data
            else:
                # Merge with existing
                data['pages'][page_key].update(page_data)

        print(f"  ✓ Updated pages section with {len(PAGES_SECTIONS[lang_code])} entries")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ {file_path.name} updated successfully!")

def main():
    """Update pages section in ES and FR."""
    print("="*70)
    print("  Updating Pages Section (ES, FR)")
    print("="*70)

    for lang_code in ['es', 'fr']:
        try:
            update_pages(lang_code)
        except Exception as e:
            print(f"  ✗ Error updating {lang_code}.json: {e}")

    print("\n" + "="*70)
    print("  DONE! Pages section updated.")
    print("="*70)

if __name__ == '__main__':
    main()
