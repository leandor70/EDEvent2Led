"""
update_remaining_i18n.py
Updates DE, ES, FR translation files with missing sections (buttons + new sections)
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Translations for buttons section (to be added)
BUTTONS_ADDITIONS = {
    "de": {
        "start_monitoring": "Überwachung starten",
        "stop_monitoring": "Überwachung stoppen",
        "flash_test": "Flash-Test",
        "export_info": "Info exportieren",
        "turn_off_selected": "Ausgewählte ausschalten",
        "preview_all": "Vorschau auf allen Geräten",
        "effect_preview": "Effekt-Vorschau",
        "hardware_modes": "Hardware-Modi",
        "revert": "Zurücksetzen"
    },
    "es": {
        "start_monitoring": "Iniciar Monitoreo",
        "stop_monitoring": "Detener Monitoreo",
        "flash_test": "Prueba Flash",
        "export_info": "Exportar Info",
        "turn_off_selected": "Apagar Seleccionados",
        "preview_all": "Vista Previa en Todos los Dispositivos",
        "effect_preview": "Vista Previa del Efecto",
        "hardware_modes": "Modos de Hardware",
        "revert": "Revertir"
    },
    "fr": {
        "start_monitoring": "Démarrer la Surveillance",
        "stop_monitoring": "Arrêter la Surveillance",
        "flash_test": "Test Flash",
        "export_info": "Exporter Info",
        "turn_off_selected": "Éteindre Sélectionnés",
        "preview_all": "Aperçu sur Tous les Appareils",
        "effect_preview": "Aperçu de l'Effet",
        "hardware_modes": "Modes Matériels",
        "revert": "Rétablir"
    }
}

# New sections to add (after modals)
NEW_SECTIONS = {
    "de": {
        "common": {
            "loading": "Wird geladen...",
            "loading_logs": "Protokolle werden geladen...",
            "all": "Alle",
            "category": "Kategorie:",
            "general": "Allgemein",
            "total_entries": "Gesamteinträge:",
            "errors": "Fehler:",
            "warnings": "Warnungen:",
            "event": "Ereignis",
            "status": "Status"
        },
        "tooltips": {
            "deassign_filtered": "Effekte von gefilterten Ereignissen entfernen",
            "delete_effect": "Effekt löschen",
            "revert_tooltip": "Zum letzten gespeicherten Zustand zurückkehren"
        },
        "alt_text": {
            "background_image": "Spiralgalaxie Hintergrund"
        },
        "event_categories": {
            "startup": "Start",
            "travel": "Reise",
            "combat": "Kampf",
            "exploration": "Erkundung",
            "trade": "Handel",
            "station": "Station",
            "powerplay": "Powerplay",
            "squadrons": "Staffeln",
            "fleet_carriers": "Flottenträger",
            "odyssey": "Odyssey"
        },
        "device_testing": {
            "test_description": "Testen Sie Ihre Bibliothekseffekte auf echter Hardware",
            "preview_description": "Die Vorschau führt die vollständige Effektsequenz auf allen angeschlossenen Geräten aus. Erstellen und bearbeiten Sie Effekte im Effekt-Editor.",
            "hardware_modes_info": "Hardware-Modi laufen auf der Gerätefirmware mit null CPU-Auslastung. Steuern Sie Geschwindigkeit und Farben direkt von der Hardware."
        },
        "keyboard_designer_sections": {
            "color_presets_title": "Farbvoreinstellungen",
            "save_preset": "VOREINSTELLUNG SPEICHERN",
            "load_profile": "Tastenbelegungsprofil laden",
            "apply_colors": "Farben auf Tastatur anwenden",
            "clear_all": "Alle Farben löschen",
            "gradient_tool": "Farbverlaufswerkzeug",
            "led_info_title": "LED-Info"
        }
    },
    "es": {
        "common": {
            "loading": "Cargando...",
            "loading_logs": "Cargando registros...",
            "all": "Todos",
            "category": "Categoría:",
            "general": "General",
            "total_entries": "Entradas totales:",
            "errors": "Errores:",
            "warnings": "Advertencias:",
            "event": "Evento",
            "status": "Estado"
        },
        "tooltips": {
            "deassign_filtered": "Desasignar efectos de eventos filtrados",
            "delete_effect": "Eliminar efecto",
            "revert_tooltip": "Volver al último estado guardado"
        },
        "alt_text": {
            "background_image": "Fondo de Galaxia Espiral"
        },
        "event_categories": {
            "startup": "Inicio",
            "travel": "Viaje",
            "combat": "Combate",
            "exploration": "Exploración",
            "trade": "Comercio",
            "station": "Estación",
            "powerplay": "Powerplay",
            "squadrons": "Escuadrones",
            "fleet_carriers": "Portanaves",
            "odyssey": "Odyssey"
        },
        "device_testing": {
            "test_description": "Pruebe los efectos de su biblioteca en hardware real",
            "preview_description": "La vista previa ejecuta la secuencia completa del efecto en todos los dispositivos conectados. Cree y edite efectos en el Editor de Efectos.",
            "hardware_modes_info": "Los modos de hardware se ejecutan en el firmware del dispositivo con cero uso de CPU. Controle la velocidad y los colores directamente desde el hardware."
        },
        "keyboard_designer_sections": {
            "color_presets_title": "Presets de Color",
            "save_preset": "GUARDAR PRESET",
            "load_profile": "Cargar Perfil de Teclas",
            "apply_colors": "Aplicar Colores al Teclado",
            "clear_all": "Borrar Todos los Colores",
            "gradient_tool": "Herramienta de Gradiente",
            "led_info_title": "Info LED"
        }
    },
    "fr": {
        "common": {
            "loading": "Chargement...",
            "loading_logs": "Chargement des journaux...",
            "all": "Tous",
            "category": "Catégorie:",
            "general": "Général",
            "total_entries": "Entrées totales:",
            "errors": "Erreurs:",
            "warnings": "Avertissements:",
            "event": "Événement",
            "status": "Statut"
        },
        "tooltips": {
            "deassign_filtered": "Désassigner les effets des événements filtrés",
            "delete_effect": "Supprimer l'effet",
            "revert_tooltip": "Revenir au dernier état enregistré"
        },
        "alt_text": {
            "background_image": "Arrière-plan Galaxie Spirale"
        },
        "event_categories": {
            "startup": "Démarrage",
            "travel": "Voyage",
            "combat": "Combat",
            "exploration": "Exploration",
            "trade": "Commerce",
            "station": "Station",
            "powerplay": "Powerplay",
            "squadrons": "Escadrons",
            "fleet_carriers": "Porte-vaisseaux",
            "odyssey": "Odyssey"
        },
        "device_testing": {
            "test_description": "Testez vos effets de bibliothèque sur du matériel réel",
            "preview_description": "L'aperçu exécute la séquence complète de l'effet sur tous les appareils connectés. Créez et modifiez des effets dans l'Éditeur d'Effets.",
            "hardware_modes_info": "Les modes matériels s'exécutent sur le firmware de l'appareil avec zéro utilisation du CPU. Contrôlez la vitesse et les couleurs directement depuis le matériel."
        },
        "keyboard_designer_sections": {
            "color_presets_title": "Préréglages de Couleur",
            "save_preset": "ENREGISTRER PRÉRÉGLAGE",
            "load_profile": "Charger Profil de Touches",
            "apply_colors": "Appliquer les Couleurs au Clavier",
            "clear_all": "Effacer Toutes les Couleurs",
            "gradient_tool": "Outil de Dégradé",
            "led_info_title": "Info LED"
        }
    }
}

def update_translation_file(lang_code: str):
    """Update translation file with missing keys."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add button additions
    if 'buttons' in data and lang_code in BUTTONS_ADDITIONS:
        for key, value in BUTTONS_ADDITIONS[lang_code].items():
            data['buttons'][key] = value
        print(f"  ✓ Added {len(BUTTONS_ADDITIONS[lang_code])} button keys")

    # Add new sections
    if lang_code in NEW_SECTIONS:
        for section_name, section_data in NEW_SECTIONS[lang_code].items():
            data[section_name] = section_data
        print(f"  ✓ Added {len(NEW_SECTIONS[lang_code])} new sections")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ {file_path.name} updated successfully!")

def main():
    """Update all remaining translation files."""
    print("="*70)
    print("  Updating Remaining Translation Files (DE, ES, FR)")
    print("="*70)

    for lang_code in ['de', 'es', 'fr']:
        try:
            update_translation_file(lang_code)
        except Exception as e:
            print(f"  ✗ Error updating {lang_code}.json: {e}")

    print("\n" + "="*70)
    print("  DONE! All translation files updated.")
    print("="*70)

if __name__ == '__main__':
    main()
