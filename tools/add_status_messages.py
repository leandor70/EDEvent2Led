"""
add_status_messages.py
Adds status_messages section to IT, DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

STATUS_MESSAGES = {
    "it": {
        "connected": "Connesso",
        "not_connected": "Non connesso",
        "active": "Attivo",
        "inactive": "Inattivo",
        "devices_detected": "{{count}} dispositivo(i) rilevato(i)",
        "openrgb_not_running": "OpenRGB non in esecuzione o server SDK disabilitato",
        "searching_journal": "Ricerca journal...",
        "no_effect_mapped": "Nessun effetto mappato",
        "event_mappings_active": "{{count}} mappatura(e) evento attiva(e)",
        "start_hint": "Avvia per iniziare l'elaborazione degli eventi journal di Elite Dangerous"
    },
    "de": {
        "connected": "Verbunden",
        "not_connected": "Nicht verbunden",
        "active": "Aktiv",
        "inactive": "Inaktiv",
        "devices_detected": "{{count}} Gerät(e) erkannt",
        "openrgb_not_running": "OpenRGB läuft nicht oder SDK-Server deaktiviert",
        "searching_journal": "Suche Journal...",
        "no_effect_mapped": "Kein Effekt zugeordnet",
        "event_mappings_active": "{{count}} Ereigniszuordnung(en) aktiv",
        "start_hint": "Starten Sie, um mit der Verarbeitung von Elite Dangerous Journal-Ereignissen zu beginnen"
    },
    "es": {
        "connected": "Conectado",
        "not_connected": "No conectado",
        "active": "Activo",
        "inactive": "Inactivo",
        "devices_detected": "{{count}} dispositivo(s) detectado(s)",
        "openrgb_not_running": "OpenRGB no está ejecutándose o el servidor SDK está deshabilitado",
        "searching_journal": "Buscando journal...",
        "no_effect_mapped": "Sin efecto mapeado",
        "event_mappings_active": "{{count}} mapeo(s) de evento activo(s)",
        "start_hint": "Iniciar para comenzar a procesar eventos del journal de Elite Dangerous"
    },
    "fr": {
        "connected": "Connecté",
        "not_connected": "Non connecté",
        "active": "Actif",
        "inactive": "Inactif",
        "devices_detected": "{{count}} appareil(s) détecté(s)",
        "openrgb_not_running": "OpenRGB n'est pas en cours d'exécution ou le serveur SDK est désactivé",
        "searching_journal": "Recherche du journal...",
        "no_effect_mapped": "Aucun effet mappé",
        "event_mappings_active": "{{count}} mappage(s) d'événement actif(s)",
        "start_hint": "Démarrer pour commencer à traiter les événements du journal Elite Dangerous"
    }
}

def update_file(lang_code):
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add common.please_wait
    if 'common' in data:
        data['common']['please_wait'] = {
            'it': 'Attendere...',
            'de': 'Bitte warten...',
            'es': 'Por favor espere...',
            'fr': 'Veuillez patienter...'
        }[lang_code]

    # Add status_messages section
    data['status_messages'] = STATUS_MESSAGES[lang_code]

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Added status_messages + common.please_wait")

def main():
    print("="*70)
    print("  Adding status_messages to IT, DE, ES, FR")
    print("="*70)

    for lang in ['it', 'de', 'es', 'fr']:
        try:
            update_file(lang)
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\n" + "="*70)
    print("  DONE!")
    print("="*70)

if __name__ == '__main__':
    main()
