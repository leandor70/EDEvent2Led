"""
update_status_i18n.py
Adds status_page section to IT, DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

STATUS_PAGE = {
    "it": {
        "monitoring_label": "Monitoraggio",
        "active_alerts_label": "Alert Attivi",
        "flags_triggered": "flag attivati",
        "ship_flags_label": "Flag Nave",
        "ship_flags_desc": "Status.json — Flags",
        "odyssey_flags_label": "Flag Odyssey",
        "odyssey_flags_desc": "Status.json — Flags2",
        "filter_all": "Tutti",
        "filter_ship": "Nave",
        "filter_odyssey": "Odyssey",
        "priority_label": "Priorità",
        "priority_all": "Tutti",
        "ship_systems_title": "Sistemi Nave",
        "odyssey_title": "Odyssey / A Piedi",
        "active_count": "{count} attivi",
        "loading_ship": "Caricamento flag nave...",
        "loading_odyssey": "Caricamento flag Odyssey...",
        "polling_interval": "Polling · 750ms"
    },
    "de": {
        "monitoring_label": "Überwachung",
        "active_alerts_label": "Aktive Alarme",
        "flags_triggered": "Flags ausgelöst",
        "ship_flags_label": "Schiff-Flags",
        "ship_flags_desc": "Status.json — Flags",
        "odyssey_flags_label": "Odyssey-Flags",
        "odyssey_flags_desc": "Status.json — Flags2",
        "filter_all": "Alle",
        "filter_ship": "Schiff",
        "filter_odyssey": "Odyssey",
        "priority_label": "Priorität",
        "priority_all": "Alle",
        "ship_systems_title": "Schiffssysteme",
        "odyssey_title": "Odyssey / Zu Fuß",
        "active_count": "{count} aktiv",
        "loading_ship": "Lade Schiff-Flags...",
        "loading_odyssey": "Lade Odyssey-Flags...",
        "polling_interval": "Abfrage · 750ms"
    },
    "es": {
        "monitoring_label": "Monitoreo",
        "active_alerts_label": "Alertas Activas",
        "flags_triggered": "flags activadas",
        "ship_flags_label": "Flags de Nave",
        "ship_flags_desc": "Status.json — Flags",
        "odyssey_flags_label": "Flags de Odyssey",
        "odyssey_flags_desc": "Status.json — Flags2",
        "filter_all": "Todos",
        "filter_ship": "Nave",
        "filter_odyssey": "Odyssey",
        "priority_label": "Prioridad",
        "priority_all": "Todos",
        "ship_systems_title": "Sistemas de Nave",
        "odyssey_title": "Odyssey / A Pie",
        "active_count": "{count} activos",
        "loading_ship": "Cargando flags de nave...",
        "loading_odyssey": "Cargando flags de Odyssey...",
        "polling_interval": "Sondeo · 750ms"
    },
    "fr": {
        "monitoring_label": "Surveillance",
        "active_alerts_label": "Alertes Actives",
        "flags_triggered": "drapeaux déclenchés",
        "ship_flags_label": "Drapeaux Vaisseau",
        "ship_flags_desc": "Status.json — Flags",
        "odyssey_flags_label": "Drapeaux Odyssey",
        "odyssey_flags_desc": "Status.json — Flags2",
        "filter_all": "Tous",
        "filter_ship": "Vaisseau",
        "filter_odyssey": "Odyssey",
        "priority_label": "Priorité",
        "priority_all": "Tous",
        "ship_systems_title": "Systèmes du Vaisseau",
        "odyssey_title": "Odyssey / À Pied",
        "active_count": "{count} actifs",
        "loading_ship": "Chargement drapeaux vaisseau...",
        "loading_odyssey": "Chargement drapeaux Odyssey...",
        "polling_interval": "Sondage · 750ms"
    }
}

def update_file(lang_code: str):
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add status_page section
    if lang_code in STATUS_PAGE:
        data['status_page'] = STATUS_PAGE[lang_code]
        print(f"  [OK] Added status_page with {len(STATUS_PAGE[lang_code])} keys")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    print("="*70)
    print("  Updating Status Page (IT, DE, ES, FR)")
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
