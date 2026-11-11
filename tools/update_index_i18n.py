"""
update_index_i18n.py
Updates pages.home card descriptions + about section in DE, ES, FR translation files
"""

import json
import sys
from pathlib import Path

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Card descriptions for pages.home
HOME_CARD_DESCRIPTIONS = {
    "de": {
        "card_config_desc": "OpenRGB-Verbindung, Journal-Pfad, Sprache und Oberflacheneinstellungen.",
        "card_devices_subtitle": "Hardware",
        "card_devices_desc": "RGB-Gerate aktivieren/deaktivieren, Verhalten bei Deaktivierung konfigurieren und Effektvorschau.",
        "card_effects_desc": "Multi-Step-Effekt-Sequenzer mit Farbauswahl, Dauersteuerung und Live-Vorschau.",
        "card_events_subtitle": "Trigger",
        "card_events_desc": "Lichteffekte Elite Dangerous-Ereignissen zuweisen mit Prioritat und Aktivierungssteuerung.",
        "card_keyboard_subtitle": "2D-Matrix",
        "card_keyboard_desc": "2D-Matrix-Visualizer mit LED-Mapping, Live-Vorschau und interaktiver Tastenauswahl.",
        "card_status_desc": "Echtzeit-Schiffsstatus-Flags - Schilde, Treibstoff, Hitze, Interdiction und mehr, synchronisiert mit LED-Effekten."
    },
    "es": {
        "card_config_desc": "Conexion OpenRGB, ruta journal, idioma y preferencias de interfaz.",
        "card_devices_subtitle": "Hardware",
        "card_devices_desc": "Habilitar/deshabilitar dispositivos RGB, configurar comportamiento al deshabilitar y vista previa de efectos.",
        "card_effects_desc": "Secuenciador de efectos multi-paso con selector de colores, controles de duracion y vista previa en vivo.",
        "card_events_subtitle": "Disparadores",
        "card_events_desc": "Asignar efectos de iluminacion a eventos de Elite Dangerous con prioridad y controles de habilitacion.",
        "card_keyboard_subtitle": "Matriz 2D",
        "card_keyboard_desc": "Visualizador de matriz 2D con mapeo LED, vista previa en vivo y seleccion interactiva de teclas.",
        "card_status_desc": "Banderas de estado de nave en tiempo real - escudos, combustible, calor, interdiccion y mas, sincronizadas con efectos LED."
    },
    "fr": {
        "card_config_desc": "Connexion OpenRGB, chemin journal, langue et preferences d'interface.",
        "card_devices_subtitle": "Materiel",
        "card_devices_desc": "Activer/desactiver les peripheriques RGB, configurer le comportement a la desactivation et apercu des effets.",
        "card_effects_desc": "Sequenceur d'effets multi-etapes avec selecteur de couleurs, controles de duree et apercu en direct.",
        "card_events_subtitle": "Declencheurs",
        "card_events_desc": "Assigner des effets d'eclairage aux evenements Elite Dangerous avec priorite et controles d'activation.",
        "card_keyboard_subtitle": "Matrice 2D",
        "card_keyboard_desc": "Visualiseur de matrice 2D avec mappage LED, apercu en direct et selection interactive des touches.",
        "card_status_desc": "Drapeaux d'etat du vaisseau en temps reel - boucliers, carburant, chaleur, interdiction et plus, synchronises avec les effets LED."
    }
}

# About section
ABOUT_SECTION = {
    "de": {
        "title": "Uber ED:Event2Led",
        "intro_p1": "ED:Event2Led ist eine Echtzeit-RGB-Beleuchtungssteuerungsanwendung fur Elite Dangerous. Sie uberwacht die Journal-Dateien des Spiels und synchronisiert Ihre RGB-Hardware (Tastatur, Maus, Gehausebeleuchtung usw.) mit In-Game-Ereignissen uber OpenRGB.",
        "intro_p2": "Von Hyperraumsprungen bis zu Andockverfahren, Kampfalarmen bis zu Treibstoffwarnungen kann jedes Elite Dangerous-Ereignis einen benutzerdefinierten Lichteffekt auslosen und so ein immersives Ambiente schaffen, das uber den Bildschirm hinausgeht.",
        "requirements_title": "Systemanforderungen",
        "req_windows": "Windows 10/11 (64-bit)",
        "req_openrgb": "OpenRGB",
        "req_openrgb_desc": "RGB-Kontrollserver (Open-Source, verfugbar unter openrgb.org)",
        "req_ed": "Elite Dangerous",
        "req_ed_desc": "Journal-Dateien aktiviert (Standard)",
        "req_python": "Python 3.11+",
        "req_python_desc": "Laufzeitumgebung",
        "req_hardware": "RGB-Hardware",
        "req_hardware_desc": "Tastatur, Maus, Gehausebeleuchtung usw. (von OpenRGB unterstutzt)",
        "quick_start_title": "Schnellstart",
        "quick_start_step1_title": "Konfiguration",
        "quick_start_step1_desc": "Verbinden Sie sich mit OpenRGB, legen Sie den Elite Dangerous-Journal-Pfad fest und wahlen Sie Ihre Sprache.",
        "quick_start_step2_title": "Gerateverwaltung",
        "quick_start_step2_desc": "Aktivieren Sie die RGB-Gerate, die Sie steuern mochten, und konfigurieren Sie deren Verhalten.",
        "quick_start_step3_title": "Effekt-Editor",
        "quick_start_step3_desc": "Erstellen Sie mehrstufige Lichtsequenzen: Wahlen Sie Farben, Dauern und Ubergangstypen.",
        "quick_start_step4_title": "Ereigniszuordnung",
        "quick_start_step4_desc": "Weisen Sie jeden Effekt einem oder mehreren Elite Dangerous-Ereignissen zu und legen Sie Prioritatsstufen fest.",
        "quick_start_step5_title": "Uberwachung starten",
        "quick_start_step5_desc": "Drucken Sie die Start-Schaltflache auf dieser Seite. ED:Event2Led verarbeitet Journal-Ereignisse in Echtzeit.",
        "privacy_title": "Daten & Datenschutz",
        "privacy_p1": "ED:Event2Led arbeitet lokal. Es liest Elite Dangerous-Journal-Dateien auf Ihrem Computer und kommuniziert über localhost mit OpenRGB. Die einzige Internetverbindung ist eine optionale Suche nach neuen Versionen: Beim Start fragt die App GitHub nach der neuesten Version und sendet dabei nur ihren Namen und ihre Version. Sie können dies in den Einstellungen abschalten. Es werden keine weiteren Daten gesammelt, übertragen oder extern gespeichert. Die Konfiguration wird in lokalen JSON-Dateien im Verzeichnis config/ gespeichert.",
        "copyright_title": "Copyright & Lizenz",
        "copyright_p1": "Copyright © 2026 Stefano Indraccolo.",
        "copyright_p2": "ED:Event2Led ist Source-available-Software, keine Open-Source-Software. Der Quellcode wird unter der PolyForm Noncommercial License 1.0.0 veröffentlicht: Sie dürfen ihn für jeden nichtkommerziellen Zweck lesen, ausführen, ändern und weitergeben. Kommerzielle Nutzung ist nicht erlaubt.",
        "copyright_p3": "Die Nutzung der App beim Streamen oder Aufnehmen Ihrer Spielsitzungen, auch auf monetarisierten Kanälen, ist erlaubt. Name und Symbol kennzeichnen das Originalprojekt: eine geänderte Version muss einen anderen Namen tragen. Offizielle Builds werden nur unter github.com/leandor70/EDEvent2Led/releases veröffentlicht.",
        "disclaimer_title": "Haftungsausschluss",
        "disclaimer_p1": "ED:Event2Led ist ein unabhangiges, inoffizielles Tool und ist nicht mit Frontier Developments plc verbunden, von ihnen gebilligt oder unterstutzt. Elite Dangerous ist eine eingetragene Marke von Frontier Developments. OpenRGB ist ein separates Open-Source-Projekt, das nicht mit diesem Tool verbunden ist.",
        "disclaimer_p2": "Diese Software wird wie besehen bereitgestellt, ohne Gewahrleistung jeglicher Art. Der Autor ubernimmt keine Verantwortung fur Hardwareschaden, Spielinstabilitat, Datenverlust oder andere direkte oder indirekte Schaden, die durch die Verwendung entstehen. Verwendung auf eigenes Risiko."
    },
    "es": {
        "title": "Acerca de ED:Event2Led",
        "intro_p1": "ED:Event2Led es una aplicacion de control de iluminacion RGB en tiempo real para Elite Dangerous. Monitorea los archivos journal del juego y sincroniza tu hardware RGB (teclado, mouse, iluminacion de gabinete, etc.) con eventos en el juego usando OpenRGB.",
        "intro_p2": "Desde saltos hiperespaciales hasta procedimientos de acoplamiento, alertas de combate hasta advertencias de combustible, cada evento de Elite Dangerous puede activar un efecto de iluminacion personalizado, creando una experiencia ambiental inmersiva que se extiende mas alla de la pantalla.",
        "requirements_title": "Requisitos del Sistema",
        "req_windows": "Windows 10/11 (64-bit)",
        "req_openrgb": "OpenRGB",
        "req_openrgb_desc": "Servidor de control RGB (codigo abierto, disponible en openrgb.org)",
        "req_ed": "Elite Dangerous",
        "req_ed_desc": "Archivos journal habilitados (predeterminado)",
        "req_python": "Python 3.11+",
        "req_python_desc": "Entorno de ejecucion",
        "req_hardware": "Hardware RGB",
        "req_hardware_desc": "Teclado, mouse, iluminacion de gabinete, etc. (compatible con OpenRGB)",
        "quick_start_title": "Inicio Rapido",
        "quick_start_step1_title": "Configuracion",
        "quick_start_step1_desc": "Conecte a OpenRGB, establezca la ruta del journal de Elite Dangerous y elija su idioma.",
        "quick_start_step2_title": "Gestion de Dispositivos",
        "quick_start_step2_desc": "Habilite los dispositivos RGB que desea controlar y configure su comportamiento.",
        "quick_start_step3_title": "Editor de Efectos",
        "quick_start_step3_desc": "Cree secuencias de iluminacion multi-paso: elija colores, duraciones y tipos de transicion.",
        "quick_start_step4_title": "Mapeo de Eventos",
        "quick_start_step4_desc": "Asigne cada efecto a uno o mas eventos de Elite Dangerous y establezca niveles de prioridad.",
        "quick_start_step5_title": "Iniciar Monitoreo",
        "quick_start_step5_desc": "Presione el boton Iniciar en esta pagina. ED:Event2Led procesara eventos del journal en tiempo real.",
        "privacy_title": "Datos y Privacidad",
        "privacy_p1": "ED:Event2Led funciona en local. Lee los archivos journal de Elite Dangerous en su equipo y se comunica con OpenRGB a través de localhost. La única conexión a internet es una comprobación opcional de nuevas versiones: al iniciar, la aplicación consulta a GitHub la última versión publicada, enviando solo su nombre y su versión. Puede desactivarla en Configuración. No se recopilan, transmiten ni almacenan externamente otros datos. La configuración se guarda en archivos JSON locales en el directorio config/.",
        "copyright_title": "Copyright y Licencia",
        "copyright_p1": "Copyright © 2026 Stefano Indraccolo.",
        "copyright_p2": "ED:Event2Led es software de código disponible (source-available), no de código abierto. Su código fuente se publica bajo la licencia PolyForm Noncommercial 1.0.0: puede leerlo, ejecutarlo, modificarlo y compartirlo para cualquier fin no comercial. No se permite el uso comercial.",
        "copyright_p3": "Se permite usar la aplicación mientras transmite o graba sus partidas, también en canales monetizados. El nombre y el icono identifican el proyecto original: una versión modificada debe usar otro nombre. Las versiones oficiales solo se publican en github.com/leandor70/EDEvent2Led/releases.",
        "disclaimer_title": "Descargo de Responsabilidad",
        "disclaimer_p1": "ED:Event2Led es una herramienta independiente y no oficial y no esta afiliada, respaldada ni apoyada por Frontier Developments plc. Elite Dangerous es una marca registrada de Frontier Developments. OpenRGB es un proyecto de codigo abierto separado no afiliado con esta herramienta.",
        "disclaimer_p2": "Este software se proporciona tal cual, sin garantia de ningun tipo. El autor no acepta responsabilidad por danos de hardware, inestabilidad del juego, perdida de datos o cualquier otro dano directo o indirecto que surja de su uso. Usar bajo su propio riesgo."
    },
    "fr": {
        "title": "A propos de ED:Event2Led",
        "intro_p1": "ED:Event2Led est une application de controle d'eclairage RGB en temps reel pour Elite Dangerous. Il surveille les fichiers journal du jeu et synchronise votre materiel RGB (clavier, souris, eclairage de boitier, etc.) avec les evenements en jeu en utilisant OpenRGB.",
        "intro_p2": "Des sauts hyperespace aux procedures d'amarrage, des alertes de combat aux avertissements de carburant, chaque evenement Elite Dangerous peut declencher un effet d'eclairage personnalise, creant une experience ambiante immersive qui s'etend au-dela de l'ecran.",
        "requirements_title": "Configuration Systeme Requise",
        "req_windows": "Windows 10/11 (64-bit)",
        "req_openrgb": "OpenRGB",
        "req_openrgb_desc": "Serveur de controle RGB (open-source, disponible sur openrgb.org)",
        "req_ed": "Elite Dangerous",
        "req_ed_desc": "Fichiers journal actives (par defaut)",
        "req_python": "Python 3.11+",
        "req_python_desc": "Environnement d'execution",
        "req_hardware": "Materiel RGB",
        "req_hardware_desc": "Clavier, souris, eclairage de boitier, etc. (pris en charge par OpenRGB)",
        "quick_start_title": "Demarrage Rapide",
        "quick_start_step1_title": "Configuration",
        "quick_start_step1_desc": "Connectez-vous a OpenRGB, definissez le chemin du journal Elite Dangerous et choisissez votre langue.",
        "quick_start_step2_title": "Gestion des Peripheriques",
        "quick_start_step2_desc": "Activez les peripheriques RGB que vous souhaitez controler et configurez leur comportement.",
        "quick_start_step3_title": "Editeur d'Effets",
        "quick_start_step3_desc": "Creez des sequences d'eclairage multi-etapes: choisissez les couleurs, les durees et les types de transition.",
        "quick_start_step4_title": "Mappage d'Evenements",
        "quick_start_step4_desc": "Assignez chaque effet a un ou plusieurs evenements Elite Dangerous et definissez les niveaux de priorite.",
        "quick_start_step5_title": "Demarrer la Surveillance",
        "quick_start_step5_desc": "Appuyez sur le bouton Demarrer sur cette page. ED:Event2Led traitera les evenements du journal en temps reel.",
        "privacy_title": "Donnees et Confidentialite",
        "privacy_p1": "ED:Event2Led fonctionne en local. Il lit les fichiers journal d'Elite Dangerous sur votre machine et communique avec OpenRGB via localhost. La seule connexion à internet est une vérification facultative des nouvelles versions : au démarrage, l'application demande à GitHub la dernière version publiée, en n'envoyant que son nom et sa version. Vous pouvez la désactiver dans les Paramètres. Aucune autre donnée n'est collectée, transmise ou stockée à l'extérieur. La configuration est enregistrée dans des fichiers JSON locaux dans le répertoire config/.",
        "copyright_title": "Copyright et Licence",
        "copyright_p1": "Copyright © 2026 Stefano Indraccolo.",
        "copyright_p2": "ED:Event2Led est un logiciel à source disponible (source-available), et non open source. Son code source est publié sous la licence PolyForm Noncommercial 1.0.0 : vous pouvez le lire, l'exécuter, le modifier et le partager à toute fin non commerciale. L'usage commercial n'est pas autorisé.",
        "copyright_p3": "L'utilisation de l'application pendant que vous diffusez ou enregistrez vos parties, y compris sur des chaînes monétisées, est autorisée. Le nom et l'icône identifient le projet original : une version modifiée doit porter un autre nom. Les versions officielles sont publiées uniquement sur github.com/leandor70/EDEvent2Led/releases.",
        "disclaimer_title": "Clause de Non-Responsabilite",
        "disclaimer_p1": "ED:Event2Led est un outil independant et non officiel et n'est pas affilie, approuve ou soutenu par Frontier Developments plc. Elite Dangerous est une marque deposee de Frontier Developments. OpenRGB est un projet open-source separe non affilie a cet outil.",
        "disclaimer_p2": "Ce logiciel est fourni tel quel, sans garantie d'aucune sorte. L'auteur n'accepte aucune responsabilite pour les dommages materiels, l'instabilite du jeu, la perte de donnees ou tout autre dommage direct ou indirect decoulant de son utilisation. Utiliser a vos propres risques."
    }
}

def update_file(lang_code: str):
    """Update pages.home card descriptions + add about section to translation file."""
    i18n_dir = Path('web/config/i18n')
    file_path = i18n_dir / f'{lang_code}.json'

    print(f"\n[{lang_code.upper()}] Updating {file_path.name}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Add card descriptions to pages.home
    if 'pages' in data and 'home' in data['pages']:
        if lang_code in HOME_CARD_DESCRIPTIONS:
            data['pages']['home'].update(HOME_CARD_DESCRIPTIONS[lang_code])
            print(f"  [OK] Added {len(HOME_CARD_DESCRIPTIONS[lang_code])} card descriptions to pages.home")

    # 2. Add about section at root level
    if lang_code in ABOUT_SECTION:
        data['about'] = ABOUT_SECTION[lang_code]
        print(f"  [OK] Added about section with {len(ABOUT_SECTION[lang_code])} keys")

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {file_path.name} updated successfully!")

def main():
    """Update pages.home + about section in DE, ES, FR."""
    print("="*70)
    print("  Updating Index Page Translations (DE, ES, FR)")
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
