"""
add_welcome_modal_i18n.py
Adds welcome_modal translation keys to DE, ES, FR
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

WELCOME_MODAL = {
    "de": {
        "title": "Willkommen bei ED:Event2Led",
        "version": "v0.5 Alpha",
        "how_it_works": "Wie es Funktioniert",
        "description": "Echtzeit-RGB-Synchronisation für Elite Dangerous Events",
        "support_title": "Entwicklung Unterstützen",
        "support_message": "ED:Event2Led wird kostenlos in meiner Freizeit entwickelt und gepflegt. Ich schenke es gerne der wunderbaren Elite Dangerous Community. Wenn Sie das Ergebnis, die Frucht tausender Stunden Studium und Implementierung, schätzen, können Sie eine freie Spende tätigen. Ihre Unterstützung hilft mir, einige Kosten zu decken (LED-Geräte, Studienmaterialien usw.) und ermöglicht es mir, weiterhin Features hinzuzufügen, Bugs zu beheben und diese Software zu unterstützen. Auch ein kleiner Beitrag wird sehr geschätzt!",
        "donate_paypal": "Spenden via PayPal",
        "donate_kofi": "Unterstützen auf Ko-fi",
        "links_title": "Nützliche Links",
        "link_documentation": "Dokumentation",
        "link_report_bug": "Bug Melden",
        "link_changelog": "Changelog",
        "link_quick_guide": "Schnellstart",
        "dont_show_again": "Diese Nachricht nicht mehr anzeigen",
        "get_started": "Los Geht's",
        "close": "Schließen"
    },
    "es": {
        "title": "Bienvenido a ED:Event2Led",
        "version": "v0.5 Alpha",
        "how_it_works": "Cómo Funciona",
        "description": "Sincronización RGB en tiempo real para eventos de Elite Dangerous",
        "support_title": "Apoya el Desarrollo",
        "support_message": "ED:Event2Led se desarrolla y mantiene gratuitamente en mi tiempo libre. Lo regalo con gusto a la maravillosa comunidad de Elite Dangerous. Si aprecias el resultado, fruto de miles de horas de estudio e implementación, puedes hacer una donación libre. Tu apoyo me ayuda a cubrir algunos costos (dispositivos LED, material de estudio, etc.) y me permite seguir añadiendo funciones, corrigiendo errores y manteniendo este software. ¡Incluso una pequeña contribución es muy apreciada!",
        "donate_paypal": "Donar vía PayPal",
        "donate_kofi": "Apoyar en Ko-fi",
        "links_title": "Enlaces Útiles",
        "link_documentation": "Documentación",
        "link_report_bug": "Reportar un Error",
        "link_changelog": "Registro de Cambios",
        "link_quick_guide": "Guía Rápida",
        "dont_show_again": "No mostrar más este mensaje",
        "get_started": "Comenzar",
        "close": "Cerrar"
    },
    "fr": {
        "title": "Bienvenue dans ED:Event2Led",
        "version": "v0.5 Alpha",
        "how_it_works": "Comment Ça Marche",
        "description": "Synchronisation RGB en temps réel pour les événements Elite Dangerous",
        "support_title": "Soutenir le Développement",
        "support_message": "ED:Event2Led est développé et maintenu gratuitement pendant mon temps libre. Je l'offre volontiers à la merveilleuse communauté Elite Dangerous. Si vous appréciez le résultat, fruit de milliers d'heures d'étude et de mise en œuvre, vous pouvez faire un don libre. Votre soutien m'aide à couvrir certains coûts (appareils LED, matériel d'étude, etc.) et me permet de continuer à ajouter des fonctionnalités, corriger des bugs et supporter ce logiciel. Même une petite contribution est grandement appréciée!",
        "donate_paypal": "Faire un Don via PayPal",
        "donate_kofi": "Soutenir sur Ko-fi",
        "links_title": "Liens Utiles",
        "link_documentation": "Documentation",
        "link_report_bug": "Signaler un Bug",
        "link_changelog": "Journal des Modifications",
        "link_quick_guide": "Guide Rapide",
        "dont_show_again": "Ne plus afficher ce message",
        "get_started": "Commencer",
        "close": "Fermer"
    }
}

def update_file(lang_code: str):
    """Add welcome_modal keys to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add welcome_modal section
    data['welcome_modal'] = WELCOME_MODAL[lang_code]
    print(f"  [OK] Added welcome_modal with 16 keys")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Add welcome_modal keys to DE, ES, FR."""
    print("="*70)
    print("  Adding Welcome Modal Keys (DE, ES, FR)")
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
