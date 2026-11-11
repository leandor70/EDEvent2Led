"""
update_events_page_i18n.py
Updates events_page section in DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

EVENTS_PAGE_SECTIONS = {
    "de": {
        "importance_label": "Wichtigkeit",
        "importance_all": "Alle",
        "results_mapped": "Ereignisse zugeordnet",
        "results_total": "gesamt",
        "modal_assign_to": "Effekt zuweisen an",
        "modal_priority": "Priorität",
        "modal_search_placeholder": "Effekte suchen...",
        "modal_create_new": "Neuen Effekt erstellen",
        "modal_no_effects": "Keine Effekte gefunden",
        "modal_no_effect_btn": "Kein Effekt",
        "modal_save": "Speichern",
        "deassign_modal_title": "Zuweisung aufheben bestätigen",
        "deassign_modal_header": "Effekte entfernen",
        "deassign_active_filters": "Aktive Filter",
        "deassign_count_text": "Ereignisse werden entfernt",
        "deassign_cancel": "Abbrechen",
        "deassign_confirm": "Entfernen"
    },
    "es": {
        "importance_label": "Importancia",
        "importance_all": "Todos",
        "results_mapped": "eventos mapeados",
        "results_total": "total",
        "modal_assign_to": "Asignar efecto a",
        "modal_priority": "Prioridad",
        "modal_search_placeholder": "Buscar efectos...",
        "modal_create_new": "Crear Nuevo Efecto",
        "modal_no_effects": "No se encontraron efectos",
        "modal_no_effect_btn": "Sin Efecto",
        "modal_save": "Guardar",
        "deassign_modal_title": "Confirmar Desasignación",
        "deassign_modal_header": "Desasignar Efectos",
        "deassign_active_filters": "Filtros activos",
        "deassign_count_text": "eventos serán desasignados",
        "deassign_cancel": "Cancelar",
        "deassign_confirm": "Desasignar"
    },
    "fr": {
        "importance_label": "Importance",
        "importance_all": "Tous",
        "results_mapped": "événements mappés",
        "results_total": "total",
        "modal_assign_to": "Assigner effet à",
        "modal_priority": "Priorité",
        "modal_search_placeholder": "Rechercher effets...",
        "modal_create_new": "Créer Nouvel Effet",
        "modal_no_effects": "Aucun effet trouvé",
        "modal_no_effect_btn": "Aucun Effet",
        "modal_save": "Enregistrer",
        "deassign_modal_title": "Confirmer Désassignation",
        "deassign_modal_header": "Désassigner Effets",
        "deassign_active_filters": "Filtres actifs",
        "deassign_count_text": "événements seront désassignés",
        "deassign_cancel": "Annuler",
        "deassign_confirm": "Désassigner"
    }
}

def update_file(lang_code: str):
    """Add events_page section to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating events_page in {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add events_page section before keyboard_designer_sections
    if lang_code in EVENTS_PAGE_SECTIONS:
        # Get ordered keys
        keys = list(data.keys())
        # Find position of keyboard_designer_sections
        if 'keyboard_designer_sections' in keys:
            idx = keys.index('keyboard_designer_sections')
            # Rebuild dict with events_page inserted before keyboard_designer_sections
            new_data = {}
            for i, k in enumerate(keys):
                if i == idx:
                    new_data['events_page'] = EVENTS_PAGE_SECTIONS[lang_code]
                new_data[k] = data[k]
            data = new_data
        else:
            # Fallback: add at end
            data['events_page'] = EVENTS_PAGE_SECTIONS[lang_code]

        print(f"  [OK] Added events_page with {len(EVENTS_PAGE_SECTIONS[lang_code])} keys")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Update events_page section in DE, ES, FR."""
    print("="*70)
    print("  Updating Events Page Sections (DE, ES, FR)")
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
