# Guida all'Integrazione del Sistema Unificato RGB

## 🎯 Obiettivo

Integrare il sistema unificato di gestione RGB con rilevamento topologia 1D/2D nell'applicazione esistente ED:Event2Led, rendendolo completamente configurabile via interfaccia grafica.

## 📋 Modifiche Necessarie

### 1. Aggiornare `src/main.py`

Sostituire il vecchio `LEDController` con il nuovo `UnifiedEffectManager`:

```python
# BEFORE
from led_controller import LEDController
from event_processor import EventProcessor

# Initialize
led_controller = LEDController()
led_controller.connect()
event_processor = EventProcessor(led_controller)

# AFTER
from openrgb import OpenRGBClient
from effects.unified_effect_manager import UnifiedEffectManager
from unified_event_processor import UnifiedEventProcessor

# Initialize
try:
    client = OpenRGBClient()
    effect_manager = UnifiedEffectManager(client)
    event_processor = UnifiedEventProcessor(effect_manager)

    print(f"Unified system initialized with {len(effect_manager.devices)} devices")
    effect_manager.print_device_summary()

except ConnectionRefusedError:
    print("ERROR: Could not connect to OpenRGB")
    effect_manager = None
    event_processor = None
```

### 2. Aggiornare `src/ui/main_window.py`

Modificare il costruttore per usare il nuovo sistema:

```python
# BEFORE
class MainWindow(QMainWindow):
    def __init__(self, led_controller, event_processor, settings, i18n):
        # ...

# AFTER
class MainWindow(QMainWindow):
    def __init__(self, effect_manager, event_processor, settings, i18n):
        super().__init__()

        self.effect_manager = effect_manager  # Changed from led_controller
        self.event_processor = event_processor
        self.settings = settings
        self.i18n = i18n
        # ...

    def _setup_ui(self):
        # ...
        # Replace DeviceConfigTab with UnifiedDeviceConfigTab
        from .unified_device_config_tab import UnifiedDeviceConfigTab

        self.device_tab = UnifiedDeviceConfigTab(
            self.effect_manager,  # Pass effect_manager instead of led_controller
            self.settings,
            self.i18n
        )
        self.tabs.addTab(self.device_tab, self.i18n.t('tab_devices'))

        # Add new event mapper tab
        from .unified_event_mapper_tab import UnifiedEventMapperTab

        self.event_mapper_tab = UnifiedEventMapperTab(
            self.effect_manager,
            self.settings,
            self.i18n
        )
        self.tabs.addTab(self.event_mapper_tab, "Event Mapper")

        # ... rest of tabs ...

    def _update_status_label(self):
        """Update connection status."""
        if self.effect_manager:
            device_count = len(self.effect_manager.devices)
            self.status_label.setText(
                f"<b>OpenRGB Connected</b> ({device_count} devices)"
            )
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("<b>OpenRGB Not Connected</b>")
            self.status_label.setStyleSheet("color: red;")

    def _on_start_clicked(self):
        """Handle start button."""
        # Save configurations
        self.device_tab._save_configuration()
        self.event_mapper_tab._save_mappings()

        # Check connection
        if not self.effect_manager:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please ensure OpenRGB is running with SDK Server enabled."
            )
            return

        # ... rest of start logic ...

    def _on_stop_clicked(self):
        """Handle stop button."""
        if self.journal_reader:
            self.journal_reader.stop()
            self.journal_reader = None

        # Clear all effects
        if self.effect_manager:
            self.effect_manager.clear_all()

        # ... rest of stop logic ...
```

### 3. Aggiungere Traduzioni (i18n)

Aggiungere le nuove chiavi di traduzione:

```python
# In your i18n file
translations = {
    # ... existing translations ...

    # Device config
    "unified_device_config": "Unified Device Configuration",
    "topology_detection_enabled": "Automatic 1D/2D topology detection enabled",
    "refresh_devices": "Refresh Devices",
    "save_configuration": "Save Configuration",
    "default_effect": "Default Effect",
    "test": "Test",
    "duration": "Duration",
    "refresh_complete": "Refresh Complete",
    "devices_detected": "devices detected",
    "refresh_failed": "Refresh Failed",
    "failed_to_refresh": "Failed to refresh devices",
    "saved": "Saved",
    "configuration_saved": "Configuration saved successfully",
    "devices_enabled": "devices enabled",

    # Event mapper
    "event_effect_mapper": "Event-to-Effect Mapper",
    "map_ed_events_to_effects": "Map Elite Dangerous events to RGB effects",
    "save_mappings": "Save Mappings",
    "test_effect": "Test Effect",
    "events_configured": "events configured",
}
```

### 4. Aggiornare Settings per Salvare Nuovi Config

In `settings.py` o equivalente, assicurarsi che supporti:

```python
# Default settings structure
default_settings = {
    # ... existing settings ...

    # Unified system settings
    "unified_device_config": {
        "enabled_devices": [],
        "device_effects": {}
    },
    "unified_event_mappings": {},
}
```

## 🚀 Lancio dell'Applicazione

### main.py Completo

```python
"""
ED:Event2Led Main Entry Point.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Material theme
from qt_material import apply_stylesheet

# OpenRGB and unified system
from openrgb import OpenRGBClient
from effects.unified_effect_manager import UnifiedEffectManager
from unified_event_processor import UnifiedEventProcessor

# UI
from ui.main_window import MainWindow

# Settings and i18n
from settings import Settings
from i18n import I18N


def main():
    """Main application entry point."""
    # Create Qt application
    app = QApplication(sys.argv)

    # Apply material theme
    apply_stylesheet(app, theme='dark_teal.xml')

    # Load settings
    settings = Settings()
    i18n = I18N(settings.get_language())

    # Initialize unified RGB system
    effect_manager = None
    event_processor = None

    try:
        print("Connecting to OpenRGB...")
        client = OpenRGBClient()

        effect_manager = UnifiedEffectManager(client)
        event_processor = UnifiedEventProcessor(effect_manager)

        print(f"✓ Unified Effect System initialized")
        effect_manager.print_device_summary()

    except ConnectionRefusedError:
        print("⚠ WARNING: Could not connect to OpenRGB")
        print("  Please ensure:")
        print("  1. OpenRGB is installed and running")
        print("  2. SDK Server is enabled in OpenRGB settings")
        print("  3. No firewall is blocking localhost connections")
        print()
        print("  Application will continue but RGB features will be disabled.")

    except Exception as e:
        print(f"⚠ ERROR initializing RGB system: {e}")
        import traceback
        traceback.print_exc()

    # Create main window
    window = MainWindow(effect_manager, event_processor, settings, i18n)
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

## 📁 Struttura File Finale

```
ED:Event2Led/
├── src/
│   ├── main.py                              # ✏️ MODIFIED
│   ├── effects/
│   │   ├── __init__.py                      # ✅ CREATED
│   │   ├── device_topology.py               # ✅ CREATED
│   │   ├── keyboard_matrix_2d.py            # ✅ CREATED
│   │   ├── linear_1d.py                     # ✅ CREATED
│   │   ├── animated_2d_effects.py           # ✅ CREATED
│   │   ├── animated_1d_effects.py           # ✅ CREATED
│   │   ├── unified_effect_manager.py        # ✅ CREATED
│   │   ├── effect.py                        # ⚪ EXISTING
│   │   └── effect_library.py                # ⚪ EXISTING
│   ├── unified_event_processor.py           # ✅ CREATED
│   ├── ui/
│   │   ├── main_window.py                   # ✏️ MODIFIED
│   │   ├── unified_device_config_tab.py     # ✅ CREATED
│   │   ├── unified_event_mapper_tab.py      # ✅ CREATED
│   │   ├── device_config_tab.py             # ⚪ KEEP (backwards compat)
│   │   └── ...                              # ⚪ EXISTING
│   ├── led_controller.py                    # ⚪ KEEP (backwards compat)
│   └── event_processor.py                   # ⚪ KEEP (backwards compat)
├── config/
│   └── unified_event_mappings_example.json  # ✅ CREATED
├── demo_unified_effects.py                  # ✅ CREATED (for testing)
├── example_integration.py                   # ✅ CREATED (for testing)
├── INTEGRATION_GUIDE.md                     # ✅ THIS FILE
├── UNIFIED_SYSTEM_README.md                 # ✅ CREATED
└── UNIFIED_EFFECTS_GUIDE.md                 # ✅ CREATED
```

## ✅ Checklist Integrazione

### Prima dell'Integrazione
- [ ] Backup del codice esistente
- [ ] OpenRGB installato e funzionante
- [ ] SDK Server abilitato in OpenRGB
- [ ] Dispositivi RGB rilevati in OpenRGB

### Durante l'Integrazione
- [ ] Aggiornato `main.py` con UnifiedEffectManager
- [ ] Aggiornato `ui/main_window.py` per usare nuovo sistema
- [ ] Aggiunti nuovi tab (UnifiedDeviceConfigTab, UnifiedEventMapperTab)
- [ ] Aggiunte traduzioni necessarie
- [ ] Testato avvio applicazione

### Dopo l'Integrazione
- [ ] Testare rilevamento dispositivi
- [ ] Configurare almeno un dispositivo
- [ ] Mappare almeno un evento
- [ ] Testare effetto con button "Test"
- [ ] Avviare monitoring e verificare effetti in-game

## 🧪 Testing

### 1. Test Sistema Unificato (Senza UI)
```bash
python demo_unified_effects.py
```
Verifica che tutti i dispositivi siano rilevati e gli effetti funzionino.

### 2. Test Integrazione Completa
```bash
python src/main.py
```

- Vai a tab "Devices"
- Verifica che i dispositivi mostrino topologia (2D/1D)
- Testa un effetto con button "Test"
- Vai a tab "Event Mapper"
- Configura un evento (es. FSDJump)
- Salva configurazione
- Avvia monitoring

### 3. Test In-Game
- Avvia Elite Dangerous
- Avvia ED:Event2Led
- Gioca e verifica che gli eventi triggano effetti RGB

## 🔧 Troubleshooting

### Dispositivi Non Rilevati
```python
# Test connessione OpenRGB
from openrgb import OpenRGBClient
client = OpenRGBClient()
print(f"Dispositivi: {len(client.devices)}")
for dev in client.devices:
    print(f"- {dev.name}: {len(dev.leds)} LEDs")
```

### Effetti Non Funzionano
- Verifica che i dispositivi siano abilitati nel tab "Devices"
- Controlla che almeno un evento sia mappato nel tab "Event Mapper"
- Usa button "Test" per testare singolarmente

### UI Non Carica
- Verifica che tutte le dipendenze siano installate:
  ```bash
  pip install PyQt6 qt-material openrgb-python watchdog
  ```

### Errori di Import
- Assicurati che tutti i file in `src/effects/` esistano
- Verifica `src/effects/__init__.py`

## 📚 Documentazione Aggiuntiva

- **UNIFIED_SYSTEM_README.md** - Overview sistema unificato
- **UNIFIED_EFFECTS_GUIDE.md** - Guida completa effetti e API
- **2D_EFFECTS_GUIDE.md** - Guida specifica effetti 2D

## 💡 Suggerimenti

### Migrazione Graduale
Puoi mantenere il vecchio sistema attivo e aggiungere il nuovo in parallelo:

```python
# In main.py
use_unified = settings.get("use_unified_system", False)

if use_unified:
    effect_manager = UnifiedEffectManager(client)
    event_processor = UnifiedEventProcessor(effect_manager)
else:
    led_controller = LEDController()
    event_processor = EventProcessor(led_controller)
```

### Performance
Il sistema unificato è più efficiente con dispositivi 1D che 2D. Se hai problemi di performance:
- Riduci durata effetti (< 2000ms)
- Usa effetti semplici per dispositivi 2D
- Disabilita dispositivi non necessari

### Personalizzazione
Per aggiungere nuovi effetti personalizzati:
1. Crea classe che eredita da `Animated2DEffect` o `Animated1DEffect`
2. Implementa `render_frame()`
3. Registra in `UnifiedEffectManager._create_2d_effect()` o `_create_1d_effect()`

## 🆘 Supporto

Se hai problemi:
1. Controlla i log in console
2. Verifica OpenRGB funzioni correttamente
3. Testa con `demo_unified_effects.py`
4. Controlla che tutti i file siano presenti
5. Verifica versioni dipendenze

---

**Buona integrazione! 🚀**
