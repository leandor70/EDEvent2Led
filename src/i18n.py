"""
Internationalization (i18n) support for ED:Event2Led.
Provides translations for Italian, English, Spanish, and German.
"""

TRANSLATIONS = {
    "en": {
        # System tray menu
        "tray_open_browser": "Open Browser",
        "tray_exit": "Exit",

        # Main Window
        "app_title": "ED:Event2Led - Elite Dangerous RGB Controller",
        "start_monitoring": "Start Monitoring",
        "stop_monitoring": "Stop Monitoring",
        "ready": "Ready",
        "monitoring_events": "Monitoring Elite Dangerous events...",
        "monitoring_stopped": "Monitoring stopped",
        "openrgb_connected": "OpenRGB: Connected",
        "openrgb_not_connected": "OpenRGB: Not Connected",
        "devices_enabled": "devices enabled",

        # Tabs
        "tab_devices": "Device Configuration",
        "tab_effects": "Effect Editor",
        "tab_events": "Event Mappings",
        "tab_settings": "Settings",

        # Device Configuration Tab
        "device_config_title": "Device Configuration",
        "device_config_desc": "Select which RGB devices should react to game events and configure their behavior when an effect ends.",
        "enable_device": "Enable this device for effects",
        "leds": "LEDs",
        "zones": "Zones",
        "after_effect": "After effect ends:",
        "behavior_off": "Turn Off",
        "behavior_original": "Return to Original",
        "behavior_custom": "Set Custom Color",
        "choose_color": "Choose Color",
        "test_effect": "Test Effect",
        "apply_config": "Apply Configuration",
        "device_config_saved": "Device configuration saved",
        "device_config_loaded": "Device configuration loaded",
        "no_devices_detected": "No devices detected. Make sure OpenRGB is running and connected.",

        # Device Types
        "device_ram": "RAM",
        "device_motherboard": "Motherboard",
        "device_gpu": "Graphics Card",
        "device_keyboard": "Keyboard",
        "device_mouse": "Mouse",
        "device_headset": "Headset",
        "device_other": "Other",

        # Event Configuration Tab
        "event_config_title": "Event Mappings",
        "event_config_desc": "Configure which Elite Dangerous events trigger RGB effects. Edit the config/event_mappings.json file to modify mappings.",
        "table_event": "Event",
        "table_effect": "Effect",
        "table_color": "Color",
        "table_duration": "Duration (ms)",
        "table_priority": "Priority",
        "reload_from_file": "Reload from File",
        "event_mappings_saved": "Event mappings saved",

        # Settings Tab
        "settings_title": "Settings",
        "language_setting": "Language",
        "language_desc": "Select application language (restart required)",
        "theme_setting": "Theme",
        "theme_desc": "Select application theme",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "theme_elite": "Elite Dangerous",
        "openrgb_setting": "OpenRGB Connection",
        "openrgb_host": "Host:",
        "openrgb_port": "Port:",
        "openrgb_test": "Test Connection",
        "journal_setting": "Elite Dangerous Journal",
        "journal_directory": "Journal Directory:",
        "journal_browse": "Browse...",
        "journal_use_default": "Use Default",
        "save_settings": "Save Settings",
        "settings_saved": "Settings saved",
        "settings_applied": "Settings applied successfully!",

        # Messages
        "not_connected_title": "Not Connected",
        "not_connected_msg": "OpenRGB is not connected. Please start OpenRGB and enable SDK Server.",
        "no_journal_title": "No Journal Directory",
        "no_journal_msg": "Please configure the Elite Dangerous journal directory in settings.",
        "confirm_exit_title": "Confirm Exit",
        "confirm_exit_msg": "Monitoring is still running. Stop and exit?",
        "connection_error_title": "Connection Error",
        "connection_error_msg": "Could not connect to OpenRGB.\n\nPlease make sure:\n1. OpenRGB is running\n2. SDK Server is enabled (Settings -> SDK Server)\n3. Port is not blocked by firewall",
        "connection_success": "Connected successfully!",
        "connection_failed": "Connection failed",
        "choose_directory": "Choose Directory",
        "restart_required": "Please restart the application for changes to take effect.",
    },

    "it": {
        # System tray menu
        "tray_open_browser": "Apri browser",
        "tray_exit": "Esci",

        # Main Window
        "app_title": "ED:Event2Led - Controller RGB per Elite Dangerous",
        "start_monitoring": "Avvia Monitoraggio",
        "stop_monitoring": "Ferma Monitoraggio",
        "ready": "Pronto",
        "monitoring_events": "Monitoraggio eventi Elite Dangerous...",
        "monitoring_stopped": "Monitoraggio fermato",
        "openrgb_connected": "OpenRGB: Connesso",
        "openrgb_not_connected": "OpenRGB: Non Connesso",
        "devices_enabled": "dispositivi abilitati",

        # Tabs
        "tab_devices": "Configurazione Dispositivi",
        "tab_effects": "Editor Effetti",
        "tab_events": "Mappatura Eventi",
        "tab_settings": "Impostazioni",

        # Device Configuration Tab
        "device_config_title": "Configurazione Dispositivi",
        "device_config_desc": "Seleziona quali dispositivi RGB devono reagire agli eventi di gioco e configura il loro comportamento quando un effetto termina.",
        "enable_device": "Abilita questo dispositivo per gli effetti",
        "leds": "LED",
        "zones": "Zone",
        "after_effect": "Dopo la fine dell'effetto:",
        "behavior_off": "Spegni",
        "behavior_original": "Ripristina Originale",
        "behavior_custom": "Imposta Colore Personalizzato",
        "choose_color": "Scegli Colore",
        "test_effect": "Testa Effetto",
        "apply_config": "Applica Configurazione",
        "device_config_saved": "Configurazione dispositivi salvata",
        "device_config_loaded": "Configurazione dispositivi caricata",
        "no_devices_detected": "Nessun dispositivo rilevato. Assicurati che OpenRGB sia in esecuzione e connesso.",

        # Device Types
        "device_ram": "RAM",
        "device_motherboard": "Scheda Madre",
        "device_gpu": "Scheda Video",
        "device_keyboard": "Tastiera",
        "device_mouse": "Mouse",
        "device_headset": "Cuffie",
        "device_other": "Altro",

        # Event Configuration Tab
        "event_config_title": "Mappatura Eventi",
        "event_config_desc": "Configura quali eventi di Elite Dangerous attivano effetti RGB. Modifica il file config/event_mappings.json per cambiare le mappature.",
        "table_event": "Evento",
        "table_effect": "Effetto",
        "table_color": "Colore",
        "table_duration": "Durata (ms)",
        "table_priority": "Priorità",
        "reload_from_file": "Ricarica da File",
        "event_mappings_saved": "Mappature eventi salvate",

        # Settings Tab
        "settings_title": "Impostazioni",
        "language_setting": "Lingua",
        "language_desc": "Seleziona la lingua dell'applicazione (richiede riavvio)",
        "theme_setting": "Tema",
        "theme_desc": "Seleziona il tema dell'applicazione",
        "theme_light": "Chiaro",
        "theme_dark": "Scuro",
        "theme_elite": "Elite Dangerous",
        "openrgb_setting": "Connessione OpenRGB",
        "openrgb_host": "Host:",
        "openrgb_port": "Porta:",
        "openrgb_test": "Testa Connessione",
        "journal_setting": "Journal Elite Dangerous",
        "journal_directory": "Directory Journal:",
        "journal_browse": "Sfoglia...",
        "journal_use_default": "Usa Predefinito",
        "save_settings": "Salva Impostazioni",
        "settings_saved": "Impostazioni salvate",
        "settings_applied": "Impostazioni applicate con successo!",

        # Messages
        "not_connected_title": "Non Connesso",
        "not_connected_msg": "OpenRGB non è connesso. Avvia OpenRGB e abilita il Server SDK.",
        "no_journal_title": "Nessuna Directory Journal",
        "no_journal_msg": "Configura la directory del journal di Elite Dangerous nelle impostazioni.",
        "confirm_exit_title": "Conferma Uscita",
        "confirm_exit_msg": "Il monitoraggio è ancora attivo. Fermare e uscire?",
        "connection_error_title": "Errore di Connessione",
        "connection_error_msg": "Impossibile connettersi a OpenRGB.\n\nAssicurati che:\n1. OpenRGB sia in esecuzione\n2. Il Server SDK sia abilitato (Impostazioni -> Server SDK)\n3. La porta non sia bloccata dal firewall",
        "connection_success": "Connesso con successo!",
        "connection_failed": "Connessione fallita",
        "choose_directory": "Scegli Directory",
        "restart_required": "Riavvia l'applicazione per applicare le modifiche.",
    },

    "es": {
        # System tray menu
        "tray_open_browser": "Abrir navegador",
        "tray_exit": "Salir",

        # Main Window
        "app_title": "ED:Event2Led - Controlador RGB para Elite Dangerous",
        "start_monitoring": "Iniciar Monitoreo",
        "stop_monitoring": "Detener Monitoreo",
        "ready": "Listo",
        "monitoring_events": "Monitoreando eventos de Elite Dangerous...",
        "monitoring_stopped": "Monitoreo detenido",
        "openrgb_connected": "OpenRGB: Conectado",
        "openrgb_not_connected": "OpenRGB: No Conectado",
        "devices_enabled": "dispositivos habilitados",

        # Tabs
        "tab_devices": "Configuración de Dispositivos",
        "tab_effects": "Editor de Efectos",
        "tab_events": "Mapeo de Eventos",
        "tab_settings": "Configuración",

        # Device Configuration Tab
        "device_config_title": "Configuración de Dispositivos",
        "device_config_desc": "Selecciona qué dispositivos RGB deben reaccionar a los eventos del juego y configura su comportamiento cuando termina un efecto.",
        "enable_device": "Habilitar este dispositivo para efectos",
        "leds": "LEDs",
        "zones": "Zonas",
        "after_effect": "Después del efecto:",
        "behavior_off": "Apagar",
        "behavior_original": "Volver al Original",
        "behavior_custom": "Color Personalizado",
        "choose_color": "Elegir Color",
        "test_effect": "Probar Efecto",
        "apply_config": "Aplicar Configuración",
        "device_config_saved": "Configuración de dispositivos guardada",
        "device_config_loaded": "Configuración de dispositivos cargada",
        "no_devices_detected": "No se detectaron dispositivos. Asegúrate de que OpenRGB esté ejecutándose y conectado.",

        # Device Types
        "device_ram": "RAM",
        "device_motherboard": "Placa Base",
        "device_gpu": "Tarjeta Gráfica",
        "device_keyboard": "Teclado",
        "device_mouse": "Ratón",
        "device_headset": "Auriculares",
        "device_other": "Otro",

        # Event Configuration Tab
        "event_config_title": "Mapeo de Eventos",
        "event_config_desc": "Configura qué eventos de Elite Dangerous activan efectos RGB. Edita el archivo config/event_mappings.json para modificar los mapeos.",
        "table_event": "Evento",
        "table_effect": "Efecto",
        "table_color": "Color",
        "table_duration": "Duración (ms)",
        "table_priority": "Prioridad",
        "reload_from_file": "Recargar desde Archivo",
        "event_mappings_saved": "Mapeos de eventos guardados",

        # Settings Tab
        "settings_title": "Configuración",
        "language_setting": "Idioma",
        "language_desc": "Selecciona el idioma de la aplicación (requiere reinicio)",
        "theme_setting": "Tema",
        "theme_desc": "Selecciona el tema de la aplicación",
        "theme_light": "Claro",
        "theme_dark": "Oscuro",
        "theme_elite": "Elite Dangerous",
        "openrgb_setting": "Conexión OpenRGB",
        "openrgb_host": "Host:",
        "openrgb_port": "Puerto:",
        "openrgb_test": "Probar Conexión",
        "journal_setting": "Journal Elite Dangerous",
        "journal_directory": "Directorio Journal:",
        "journal_browse": "Explorar...",
        "journal_use_default": "Usar Predeterminado",
        "save_settings": "Guardar Configuración",
        "settings_saved": "Configuración guardada",
        "settings_applied": "¡Configuración aplicada con éxito!",

        # Messages
        "not_connected_title": "No Conectado",
        "not_connected_msg": "OpenRGB no está conectado. Inicia OpenRGB y habilita el Servidor SDK.",
        "no_journal_title": "Sin Directorio Journal",
        "no_journal_msg": "Configura el directorio del journal de Elite Dangerous en la configuración.",
        "confirm_exit_title": "Confirmar Salida",
        "confirm_exit_msg": "El monitoreo aún está activo. ¿Detener y salir?",
        "connection_error_title": "Error de Conexión",
        "connection_error_msg": "No se pudo conectar a OpenRGB.\n\nAsegúrate de que:\n1. OpenRGB esté ejecutándose\n2. El Servidor SDK esté habilitado (Configuración -> Servidor SDK)\n3. El puerto no esté bloqueado por el firewall",
        "connection_success": "¡Conectado exitosamente!",
        "connection_failed": "Conexión fallida",
        "choose_directory": "Elegir Directorio",
        "restart_required": "Reinicia la aplicación para aplicar los cambios.",
    },

    "fr": {
        # System tray menu
        "tray_open_browser": "Ouvrir le navigateur",
        "tray_exit": "Quitter",
    },

    "de": {
        # System tray menu
        "tray_open_browser": "Browser öffnen",
        "tray_exit": "Beenden",

        # Main Window
        "app_title": "ED:Event2Led - RGB-Controller für Elite Dangerous",
        "start_monitoring": "Überwachung Starten",
        "stop_monitoring": "Überwachung Stoppen",
        "ready": "Bereit",
        "monitoring_events": "Elite Dangerous-Ereignisse werden überwacht...",
        "monitoring_stopped": "Überwachung gestoppt",
        "openrgb_connected": "OpenRGB: Verbunden",
        "openrgb_not_connected": "OpenRGB: Nicht Verbunden",
        "devices_enabled": "Geräte aktiviert",

        # Tabs
        "tab_devices": "Gerätekonfiguration",
        "tab_effects": "Effekt-Editor",
        "tab_events": "Ereigniszuordnung",
        "tab_settings": "Einstellungen",

        # Device Configuration Tab
        "device_config_title": "Gerätekonfiguration",
        "device_config_desc": "Wählen Sie aus, welche RGB-Geräte auf Spielereignisse reagieren sollen, und konfigurieren Sie ihr Verhalten nach Ende eines Effekts.",
        "enable_device": "Dieses Gerät für Effekte aktivieren",
        "leds": "LEDs",
        "zones": "Zonen",
        "after_effect": "Nach Effektende:",
        "behavior_off": "Ausschalten",
        "behavior_original": "Original Wiederherstellen",
        "behavior_custom": "Benutzerdefinierte Farbe",
        "choose_color": "Farbe Wählen",
        "test_effect": "Effekt Testen",
        "apply_config": "Konfiguration Anwenden",
        "device_config_saved": "Gerätekonfiguration gespeichert",
        "device_config_loaded": "Gerätekonfiguration geladen",
        "no_devices_detected": "Keine Geräte erkannt. Stellen Sie sicher, dass OpenRGB läuft und verbunden ist.",

        # Device Types
        "device_ram": "RAM",
        "device_motherboard": "Hauptplatine",
        "device_gpu": "Grafikkarte",
        "device_keyboard": "Tastatur",
        "device_mouse": "Maus",
        "device_headset": "Kopfhörer",
        "device_other": "Andere",

        # Event Configuration Tab
        "event_config_title": "Ereigniszuordnung",
        "event_config_desc": "Konfigurieren Sie, welche Elite Dangerous-Ereignisse RGB-Effekte auslösen. Bearbeiten Sie die Datei config/event_mappings.json, um Zuordnungen zu ändern.",
        "table_event": "Ereignis",
        "table_effect": "Effekt",
        "table_color": "Farbe",
        "table_duration": "Dauer (ms)",
        "table_priority": "Priorität",
        "reload_from_file": "Aus Datei Neu Laden",
        "event_mappings_saved": "Ereigniszuordnungen gespeichert",

        # Settings Tab
        "settings_title": "Einstellungen",
        "language_setting": "Sprache",
        "language_desc": "Anwendungssprache auswählen (Neustart erforderlich)",
        "theme_setting": "Design",
        "theme_desc": "Anwendungsdesign auswählen",
        "theme_light": "Hell",
        "theme_dark": "Dunkel",
        "theme_elite": "Elite Dangerous",
        "openrgb_setting": "OpenRGB-Verbindung",
        "openrgb_host": "Host:",
        "openrgb_port": "Port:",
        "openrgb_test": "Verbindung Testen",
        "journal_setting": "Elite Dangerous Journal",
        "journal_directory": "Journal-Verzeichnis:",
        "journal_browse": "Durchsuchen...",
        "journal_use_default": "Standard Verwenden",
        "save_settings": "Einstellungen Speichern",
        "settings_saved": "Einstellungen gespeichert",
        "settings_applied": "Einstellungen erfolgreich angewendet!",

        # Messages
        "not_connected_title": "Nicht Verbunden",
        "not_connected_msg": "OpenRGB ist nicht verbunden. Starten Sie OpenRGB und aktivieren Sie den SDK-Server.",
        "no_journal_title": "Kein Journal-Verzeichnis",
        "no_journal_msg": "Bitte konfigurieren Sie das Elite Dangerous Journal-Verzeichnis in den Einstellungen.",
        "confirm_exit_title": "Beenden Bestätigen",
        "confirm_exit_msg": "Die Überwachung läuft noch. Stoppen und beenden?",
        "connection_error_title": "Verbindungsfehler",
        "connection_error_msg": "Verbindung zu OpenRGB konnte nicht hergestellt werden.\n\nStellen Sie sicher, dass:\n1. OpenRGB läuft\n2. Der SDK-Server aktiviert ist (Einstellungen -> SDK-Server)\n3. Der Port nicht durch die Firewall blockiert wird",
        "connection_success": "Erfolgreich verbunden!",
        "connection_failed": "Verbindung fehlgeschlagen",
        "choose_directory": "Verzeichnis Wählen",
        "restart_required": "Bitte starten Sie die Anwendung neu, damit die Änderungen wirksam werden.",
    }
}


class I18n:
    """Internationalization helper class."""

    def __init__(self, language: str = "en"):
        """Initialize with a language code."""
        self.language = language if language in TRANSLATIONS else "en"

    def t(self, key: str) -> str:
        """
        Get translated string for a key.

        Args:
            key: Translation key

        Returns:
            Translated string, or key if translation not found
        """
        return TRANSLATIONS.get(self.language, {}).get(key, key)

    def set_language(self, language: str):
        """Set the current language."""
        if language in TRANSLATIONS:
            self.language = language

    def get_available_languages(self) -> dict:
        """Get dict of available languages with their display names."""
        return {
            "en": "English",
            "it": "Italiano",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch"
        }
