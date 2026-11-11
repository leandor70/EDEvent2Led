# Sistema Unificato di Effetti RGB per Elite Dangerous

## 🎮 Panoramica

Sistema avanzato di controllo RGB che sincronizza i LED del tuo PC (tastiera, RAM, mouse, GPU, ecc.) con gli eventi di Elite Dangerous. Rileva automaticamente la topologia dei dispositivi e applica effetti ottimizzati per ogni tipo di hardware.

## ✨ Caratteristiche

- **🔍 Rilevamento Automatico**: Identifica tastiere 2D, RAM 1D, e altri dispositivi
- **🎨 Effetti Ottimizzati**: Oltre 18 effetti diversi adattati alla topologia del dispositivo
- **🎯 Multi-Device**: Controllo coordinato di tutti i dispositivi RGB simultaneamente
- **⚡ Priorità Dinamica**: Gli eventi critici interrompono quelli meno importanti
- **🎭 Temi Predefiniti**: Effetti coordinati per eventi comuni (hyperspace, combat, docked)
- **⚙️ Configurabile**: File JSON per personalizzare ogni evento
- **🔌 OpenRGB**: Supporta tutti i dispositivi compatibili con OpenRGB

## 🚀 Quick Start

### 1. Prerequisiti

```bash
# Installa OpenRGB da https://openrgb.org/
# Abilita "SDK Server" nelle impostazioni

# Installa dipendenze Python
pip install openrgb-python PyQt6 qt-material watchdog
```

### 2. Test Dispositivi

```bash
# Rileva e analizza tutti i dispositivi
python analyze_keyboard.py

# Demo effetti multi-device
python demo_unified_effects.py
```

### 3. Esempio Integrazione

```bash
# Simula eventi di gioco
python example_integration.py
```

## 📁 Struttura File

```
ED:Event2Led/
├── src/
│   ├── effects/
│   │   ├── device_topology.py          # Rilevamento topologia
│   │   ├── keyboard_matrix_2d.py       # Controllo tastiere 2D
│   │   ├── linear_1d.py                # Controllo dispositivi 1D
│   │   ├── animated_2d_effects.py      # Effetti animati 2D
│   │   ├── animated_1d_effects.py      # Effetti animati 1D
│   │   └── unified_effect_manager.py   # Manager unificato
│   ├── unified_event_processor.py      # Processore eventi ED
│   └── led_controller.py               # Controllo LED base
├── config/
│   └── unified_event_mappings.json     # Configurazione eventi
├── demo_unified_effects.py             # Demo completa
├── example_integration.py              # Esempio integrazione
├── UNIFIED_EFFECTS_GUIDE.md            # Guida completa
└── 2D_EFFECTS_GUIDE.md                 # Guida effetti 2D
```

## 🎯 Dispositivi Supportati

### 📐 Topologia 2D (Matrix)
- **Tastiere**: Controllo individuale LED con matrice X,Y
- **Effetti**: Ripple, Wave, Esplosioni, Sweep, Cerchi

### 📏 Topologia 1D (Linear)
- **RAM**: Strip LED lineare
- **Mouse**: LED lungo il perimetro
- **GPU**: Strip LED sul bordo
- **LED Strip**: Strip generiche
- **Effetti**: Scanner, Chase, Wave, Pulse, Fill

## 🎨 Effetti Disponibili

### Effetti 2D (Tastiere)
| Effetto | Descrizione | Uso Consigliato |
|---------|-------------|------------------|
| `horizontal_sweep` | Scansione orizzontale | Supercruise, docking |
| `vertical_sweep` | Scansione verticale | Scanning, takeoff |
| `ripple` | Cerchi espandenti | Discovery, alerts |
| `wave` | Onda sinusoidale | Hyperspace, travel |
| `explosion` | Esplosione colorata | Death, critical damage |
| `imploding_circles` | Cerchi che implodono | Arrival, completion |
| `diagonal_sweep` | Scansione diagonale | Interdiction |

### Effetti 1D (RAM, Mouse, ecc.)
| Effetto | Descrizione | Uso Consigliato |
|---------|-------------|------------------|
| `wave` | Onda sinusoidale | Travel, ambient |
| `scanner` | Cylon/Knight Rider | Alert, scanning |
| `chase` | Punti inseguitori | Movement, activity |
| `rainbow` | Arcobaleno animato | Celebration, discovery |
| `fill` | Barra di progresso | Loading, fuel scoop |
| `sparkle` | Scintillio casuale | Discovery, stars |
| `pulse` | Pulsazione | Alerts, docking |
| `center_out` | Espansione centrale | Impact, arrival |

## ⚙️ Configurazione

### File JSON Base

```json
{
  "FSDJump": {
    "theme": "hyperspace",
    "priority": 8,
    "description": "Hyperspace jump"
  },
  "UnderAttack": {
    "effect": "pulse",
    "params": {
      "duration_ms": 2000,
      "color": [255, 0, 0],
      "min_brightness": 0.1
    },
    "priority": 10
  }
}
```

### Codice Python

```python
from openrgb import OpenRGBClient
from src.effects.unified_effect_manager import UnifiedEffectManager
from src.unified_event_processor import UnifiedEventProcessor

# Setup
client = OpenRGBClient()
effect_manager = UnifiedEffectManager(client)
event_processor = UnifiedEventProcessor(effect_manager)

# Carica config personalizzata (opzionale)
event_processor.load_mappings("config/unified_event_mappings.json")

# Processa evento
event_processor.process_event({"event": "FSDJump", "StarSystem": "Sol"})

# O usa effetti manuali
effect_manager.apply_themed_effect("hyperspace")
effect_manager.apply_effect_to_all("pulse", {"duration_ms": 2000, "color": (255, 0, 0)})
```

## 🎭 Temi Predefiniti

| Tema | Evento ED | Effetto 2D | Effetto 1D |
|------|-----------|------------|------------|
| `hyperspace` | FSDJump | Wave orizzontale blu | Wave veloce |
| `combat` | UnderAttack | Explosion | Pulse rosso |
| `shields_down` | ShieldState | Ripple rosso | Scanner rosso |
| `supercruise` | SupercruiseEntry | Sweep down | Chase blu |
| `discovery` | FSSSignalDiscovered | Imploding circles | Sparkle |
| `fuel_scoop` | FuelScoop | Wave verticale | Fill progress |
| `docked` | Docked | Pulse verde | Pulse verde |

## 📊 Priorità Effetti

- **10**: 🔴 Critico (morte, scudi abbattuti)
- **8-9**: 🟠 Importante (FSD jump, combattimento)
- **5-7**: 🟡 Normale (docking, scansioni)
- **1-4**: 🟢 Minore (eventi background)

Effetti ad alta priorità interrompono quelli a bassa priorità.

## 🔧 API Principali

### UnifiedEffectManager

```python
# Applica a tutti
manager.apply_effect_to_all('pulse', {'duration_ms': 2000, 'color': (255, 0, 0)})

# Applica per topologia
manager.apply_effect_by_topology(TopologyType.MATRIX, 'ripple', {...})
manager.apply_effect_by_topology(TopologyType.LINEAR, 'scanner', {...})

# Applica a device specifico
manager.apply_effect_to_device('ASUS TUF Gaming K7', 'explosion', {...})

# Tema coordinato
manager.apply_themed_effect('hyperspace')

# Clear
manager.clear_all()
```

### UnifiedEventProcessor

```python
# Processa evento ED
processor.process_event({"event": "FSDJump", ...})

# Aggiungi mapping
processor.add_mapping("CustomEvent", {
    "effect": "pulse",
    "params": {...},
    "priority": 7
})

# Stop tutto
processor.stop_all_effects()

# Stampa mappings
processor.print_mappings()
```

## 📚 Guide Complete

- **[UNIFIED_EFFECTS_GUIDE.md](UNIFIED_EFFECTS_GUIDE.md)** - Guida completa sistema unificato
- **[2D_EFFECTS_GUIDE.md](2D_EFFECTS_GUIDE.md)** - Guida dettagliata effetti tastiera
- **[CLAUDE.md](CLAUDE.md)** - Documentazione architettura progetto

## 🐛 Troubleshooting

### Dispositivi non rilevati
1. Verifica OpenRGB sia in esecuzione
2. Abilita "SDK Server" nelle impostazioni
3. Controlla che i dispositivi siano visibili in OpenRGB GUI

### Effetti non funzionano
```python
# Test connessione
from openrgb import OpenRGBClient
client = OpenRGBClient()
print(f"Dispositivi: {len(client.devices)}")
for dev in client.devices:
    print(f"- {dev.name}: {len(dev.leds)} LEDs")
```

### Performance scarse
- Riduci durata effetti (< 3000ms)
- Usa effetti 1D invece di 2D quando possibile
- Disabilita dispositivi non necessari

## 💡 Best Practices

1. **Testa prima**: Usa `demo_unified_effects.py` prima di giocare
2. **Priorità corrette**: Riserva 10 solo per eventi critici
3. **Durate brevi**: Mantieni effetti sotto i 5 secondi
4. **Colori coerenti**: Usa schema colori consistente
   - 🔴 Rosso = Pericolo/Damage
   - 🔵 Blu = Viaggio/FSD
   - 🟢 Verde = Successo/Docking
   - 🟡 Giallo = Attenzione/Warning
   - ⚪ Bianco = Neutrale/Discovery

## 🎯 Esempi Configurazioni

### Minimal (Eventi Critici)
```json
{
  "UnderAttack": {"theme": "combat", "priority": 10},
  "ShieldState": {"theme": "shields_down", "priority": 9},
  "FSDJump": {"theme": "hyperspace", "priority": 8}
}
```

### Esplorazione
```json
{
  "FSDJump": {"theme": "hyperspace", "priority": 8},
  "FSSSignalDiscovered": {"theme": "discovery", "priority": 6},
  "Scan": {"effect": "sparkle", "params": {...}, "priority": 5},
  "SASignalsFound": {"theme": "discovery", "priority": 6}
}
```

### Combat-Focused
```json
{
  "UnderAttack": {"theme": "combat", "priority": 10},
  "ShieldState": {"theme": "shields_down", "priority": 9},
  "HullDamage": {"effect": "explosion", "params": {...}, "priority": 8},
  "FighterLaunched": {"effect": "chase", "params": {...}, "priority": 7}
}
```

## 🔗 Risorse

- **OpenRGB**: https://openrgb.org/
- **Elite Journal Docs**: https://elite-journal.readthedocs.io/
- **OpenRGB Python**: https://github.com/jath03/openrgb-python

## 📝 Note

- Il sistema usa threading per effetti non-blocking
- Tutti gli effetti sono interrompibili
- La configurazione si carica automaticamente all'avvio
- I dispositivi vengono rilevati automaticamente alla connessione

## 🚀 Prossimi Passi

1. Esegui `demo_unified_effects.py` per vedere il sistema in azione
2. Personalizza `config/unified_event_mappings.json` con i tuoi eventi preferiti
3. Integra con il journal reader per uso in gameplay reale
4. Sperimenta con effetti personalizzati!

---

**Buon volo, CMDR! o7**
