"""
update_keyboard_designer_i18n.py
Updates keyboard_designer_sections in DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

KEYBOARD_DESIGNER_SECTIONS = {
    "de": {
        "subtitle": "Tastaturbelegungen laden -> Tasten nach Kategorie färben &nbsp;·&nbsp; Taste klicken -> Farbe zuweisen &nbsp;·&nbsp; Speichern auf P1 / P2 / P3",
        "live_preview": "LIVE-VORSCHAU",
        "legend_no_led": "Keine LED",
        "legend_led_visible": "LED-Index sichtbar (Live-Vorschau aus)",
        "category_colors_title": "Kategoriefarben",
        "category_colors_reset": "Zurücksetzen",
        "category_colors_reapply": "Erneut anwenden",
        "keybind_profile_title": "Keybind-Profil",
        "keybind_profile_no_profile": "Kein Profil geladen",
        "keybind_profile_placeholder": "Auto-Erkennung oder durchsuchen...",
        "keybind_profile_path_title": "Pfad zur .binds-Datei",
        "keybind_profile_browse_title": "Durchsuchen",
        "load_keybindings": "TASTATURBELEGUNGEN LADEN",
        "mode_ship": "Schiff",
        "mode_srv": "SRV",
        "mode_onfoot": "Zu Fuß",
        "bindings_label": "Belegungen",
        "bindings_filter_placeholder": "Filtern...",
        "apply_to_keyboard": "AUF TASTATUR ANWENDEN",
        "clear_profile": "Profil löschen",
        "color_presets_title": "Farbvoreinstellungen",
        "color_presets_hint": "Label klicken zum Auswählen · ↓ zum Laden von Disk",
        "load_preset_title": "{{preset}} von Disk laden",
        "save_preset": "VOREINSTELLUNG SPEICHERN",
        "preset_no_selection": "Keine Voreinstellung ausgewählt",
        "selected_key_title": "Ausgewählte Taste",
        "selected_key_hint": "Klicken Sie auf eine Taste auf der Tastatur",
        "selected_key_color_label": "Farbe:",
        "selected_key_color_title": "Klicken zum Ändern der Farbe",
        "selected_key_clear_title": "Farbe löschen (Standard wiederherstellen)",
        "quick_actions_title": "Schnellaktionen",
        "toggle_live_preview": "Live-Vorschau umschalten",
        "test_gradient": "Farbverlauf testen",
        "show_grid_lines": "Gitterlinien anzeigen",
        "clear_all_colors": "Alle Farben löschen",
        "export_matrix_json": "Matrix JSON exportieren",
        "device_info_title": "Geräteinfo",
        "device_info_device": "Gerät:",
        "device_info_total_keys": "Tasten gesamt:",
        "device_info_layout": "Layout:",
        "device_info_layout_value": "ANSI Vollständig + Numpad",
        "device_info_grid": "Gitter:",
        "device_info_grid_value": "90 Spalten × 8px",
        "device_info_led_indicators": "LED-Anzeigen:",
        "device_info_led_indicators_value": "3 (NumLock / CapsLock / ScrollLock)",
        "load_profile": "Tastenbelegungsprofil laden",
        "apply_colors": "Farben auf Tastatur anwenden",
        "clear_all": "Alle Farben löschen",
        "gradient_tool": "Farbverlaufswerkzeug",
        "led_info_title": "LED-Info"
    },
    "es": {
        "subtitle": "Cargar teclas → colorear teclas por categoría &nbsp;·&nbsp; Clic en una tecla → asignar color &nbsp;·&nbsp; Guardar en P1 / P2 / P3",
        "live_preview": "VISTA PREVIA EN VIVO",
        "legend_no_led": "Sin LED",
        "legend_led_visible": "Índice LED visible (Vista previa en vivo desactivada)",
        "category_colors_title": "Colores de Categoría",
        "category_colors_reset": "Restablecer",
        "category_colors_reapply": "Re-Aplicar",
        "keybind_profile_title": "Perfil de Teclas",
        "keybind_profile_no_profile": "Sin perfil cargado",
        "keybind_profile_placeholder": "Auto-detectar o explorar...",
        "keybind_profile_path_title": "Ruta al archivo .binds",
        "keybind_profile_browse_title": "Explorar",
        "load_keybindings": "CARGAR TECLAS",
        "mode_ship": "Nave",
        "mode_srv": "SRV",
        "mode_onfoot": "A Pie",
        "bindings_label": "Asignaciones",
        "bindings_filter_placeholder": "Filtrar...",
        "apply_to_keyboard": "APLICAR AL TECLADO",
        "clear_profile": "Borrar Perfil",
        "color_presets_title": "Presets de Color",
        "color_presets_hint": "Clic en etiqueta para seleccionar · ↓ para cargar desde disco",
        "load_preset_title": "Cargar {{preset}} desde disco",
        "save_preset": "GUARDAR PRESET",
        "preset_no_selection": "Ningún preset seleccionado",
        "selected_key_title": "Tecla Seleccionada",
        "selected_key_hint": "Haga clic en una tecla del teclado",
        "selected_key_color_label": "Color:",
        "selected_key_color_title": "Clic para cambiar color",
        "selected_key_clear_title": "Borrar color (restaurar predeterminado)",
        "quick_actions_title": "Acciones Rápidas",
        "toggle_live_preview": "Activar/Desactivar Vista Previa",
        "test_gradient": "Probar Gradiente",
        "show_grid_lines": "Mostrar Líneas de Cuadrícula",
        "clear_all_colors": "Borrar Todos los Colores",
        "export_matrix_json": "Exportar Matriz JSON",
        "device_info_title": "Info del Dispositivo",
        "device_info_device": "Dispositivo:",
        "device_info_total_keys": "Teclas Totales:",
        "device_info_layout": "Distribución:",
        "device_info_layout_value": "ANSI Completo + Numpad",
        "device_info_grid": "Cuadrícula:",
        "device_info_grid_value": "90 cols × 8px",
        "device_info_led_indicators": "Indicadores LED:",
        "device_info_led_indicators_value": "3 (BloqNum / BloqMayús / BloqDespl)",
        "load_profile": "Cargar Perfil de Teclas",
        "apply_colors": "Aplicar Colores al Teclado",
        "clear_all": "Borrar Todos los Colores",
        "gradient_tool": "Herramienta de Gradiente",
        "led_info_title": "Info LED"
    },
    "fr": {
        "subtitle": "Charger touches → colorer par catégorie &nbsp;·&nbsp; Cliquer une touche → assigner couleur &nbsp;·&nbsp; Sauvegarder sur P1 / P2 / P3",
        "live_preview": "APERÇU EN DIRECT",
        "legend_no_led": "Pas de LED",
        "legend_led_visible": "Index LED visible (Aperçu en direct désactivé)",
        "category_colors_title": "Couleurs de Catégorie",
        "category_colors_reset": "Réinitialiser",
        "category_colors_reapply": "Ré-appliquer",
        "keybind_profile_title": "Profil de Touches",
        "keybind_profile_no_profile": "Aucun profil chargé",
        "keybind_profile_placeholder": "Auto-détection ou parcourir...",
        "keybind_profile_path_title": "Chemin vers fichier .binds",
        "keybind_profile_browse_title": "Parcourir",
        "load_keybindings": "CHARGER TOUCHES",
        "mode_ship": "Vaisseau",
        "mode_srv": "SRV",
        "mode_onfoot": "À Pied",
        "bindings_label": "Liaisons",
        "bindings_filter_placeholder": "Filtrer...",
        "apply_to_keyboard": "APPLIQUER AU CLAVIER",
        "clear_profile": "Effacer Profil",
        "color_presets_title": "Préréglages de Couleur",
        "color_presets_hint": "Cliquer l'étiquette pour sélectionner · ↓ pour charger du disque",
        "load_preset_title": "Charger {{preset}} du disque",
        "save_preset": "ENREGISTRER PRÉRÉGLAGE",
        "preset_no_selection": "Aucun préréglage sélectionné",
        "selected_key_title": "Touche Sélectionnée",
        "selected_key_hint": "Cliquez sur une touche du clavier",
        "selected_key_color_label": "Couleur:",
        "selected_key_color_title": "Cliquer pour changer la couleur",
        "selected_key_clear_title": "Effacer couleur (restaurer par défaut)",
        "quick_actions_title": "Actions Rapides",
        "toggle_live_preview": "Basculer Aperçu en Direct",
        "test_gradient": "Tester Dégradé",
        "show_grid_lines": "Afficher Lignes de Grille",
        "clear_all_colors": "Effacer Toutes les Couleurs",
        "export_matrix_json": "Exporter Matrice JSON",
        "device_info_title": "Info Appareil",
        "device_info_device": "Appareil:",
        "device_info_total_keys": "Touches Totales:",
        "device_info_layout": "Disposition:",
        "device_info_layout_value": "ANSI Complet + Numpad",
        "device_info_grid": "Grille:",
        "device_info_grid_value": "90 cols × 8px",
        "device_info_led_indicators": "Indicateurs LED:",
        "device_info_led_indicators_value": "3 (VerrNum / VerrMaj / ArrêtDéfil)",
        "load_profile": "Charger Profil de Touches",
        "apply_colors": "Appliquer les Couleurs au Clavier",
        "clear_all": "Effacer Toutes les Couleurs",
        "gradient_tool": "Outil de Dégradé",
        "led_info_title": "Info LED"
    }
}

def update_file(lang_code: str):
    """Update keyboard_designer_sections in translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating keyboard_designer_sections in {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Replace keyboard_designer_sections
    if lang_code in KEYBOARD_DESIGNER_SECTIONS:
        data['keyboard_designer_sections'] = KEYBOARD_DESIGNER_SECTIONS[lang_code]
        print(f"  [OK] Replaced keyboard_designer_sections with {len(KEYBOARD_DESIGNER_SECTIONS[lang_code])} keys")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Update keyboard_designer_sections in DE, ES, FR."""
    print("="*70)
    print("  Updating Keyboard Designer Sections (DE, ES, FR)")
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
