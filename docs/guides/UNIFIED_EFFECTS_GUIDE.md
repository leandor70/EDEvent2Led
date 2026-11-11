# Guida Completa al Sistema Unificato di Effetti RGB

## Panoramica

Il **Sistema Unificato di Effetti RGB** rileva automaticamente la topologia dei tuoi dispositivi LED (tastiere 2D, RAM 1D, mouse, ecc.) e applica effetti appropriati in risposta agli eventi di Elite Dangerous.

## Architettura del Sistema

```
Elite Dangerous Journal
         ↓
[UnifiedEventProcessor]
         ↓
[UnifiedEffectManager]
         ↓
    ┌────┴────┬────────┬────────┐
    ↓         ↓        ↓        ↓
[Tastiera] [RAM]  [Mouse] [GPU]
  (2D)      (1D)    (1D)   (1D)
```

## Componenti Principali

### 1. Rilevamento Automatico Topologia
Il sistema rileva automaticamente:
- **Dispositivi 2D (Matrix)**: Tastiere con matrice LED
- **Dispositivi 1D (Linear)**: RAM, mouse, strip LED, GPU
- **Dispositivi Singoli**: Dispositivi con 1 LED o senza topologia specifica

### 2. Libreria Effetti

#### Effetti 2D (Tastiere)
- `horizontal_sweep` - Scansione orizzontale
- `vertical_sweep` - Scansione verticale
- `ripple` - Increspatura dal centro
- `wave` - Onda sinusoidale
- `explosion` - Esplosione
- `imploding_circles` - Cerchi concentrici
- `diagonal_sweep` - Scansione diagonale

#### Effetti 1D (RAM, Mouse, Strip)
- `wave` - Onda sinusoidale
- `scanner` - Effetto Cylon/Knight Rider
- `chase` - Punti che si inseguono
- `rainbow` - Arcobaleno animato
- `fill` - Barra di progresso
- `sparkle` - Scintillio casuale
- `pulse` - Pulsazione
- `center_out` - Espansione dal centro
- `pulse_from_center` - Impulso dal centro
- `gradient_shift` - Gradiente che si sposta

### 3. Temi Predefiniti
Effetti coordinati per eventi comuni:
- `hyperspace` - Salto FSD
- `combat` - Combattimento
- `shields_down` - Scudi abbattuti
- `supercruise` - Supercruise
- `discovery` - Scoperta
- `fuel_scoop` - Raccolta carburante
- `docked` - Attraccato

## Setup Rapido

### 1. Test del Sistema

```bash
# Test rilevamento dispositivi
python demo_unified_effects.py
```

Questo script:
- Rileva tutti i dispositivi
- Mostra la topologia di ognuno
- Esegue demo di tutti gli effetti
- Simula una sequenza di gioco

### 2. Integrazione con Elite Dangerous

```python
from openrgb import OpenRGBClient
from src.effects.unified_effect_manager import UnifiedEffectManager
from src.unified_event_processor import UnifiedEventProcessor
from src.journal_reader import JournalReader

# Connetti a OpenRGB
client = OpenRGBClient()

# Crea manager effetti
effect_manager = UnifiedEffectManager(client)

# Crea event processor
event_processor = UnifiedEventProcessor(effect_manager)

# Opzionale: Carica configurazione personalizzata
event_processor.load_mappings("config/unified_event_mappings.json")

# Crea journal reader
journal_reader = JournalReader()

# Collega eventi
journal_reader.on_event = event_processor.process_event

# Avvia monitoraggio
journal_reader.start()
```

## Configurazione

### File di Configurazione JSON

Crea `config/unified_event_mappings.json` per personalizzare gli effetti:

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
    "priority": 10,
    "description": "Under attack"
  }
}
```

### Struttura Configurazione

Ogni evento può usare:

**Tema** (consigliato):
```json
{
  "EventName": {
    "theme": "nome_tema",
    "priority": 1-10,
    "description": "Descrizione"
  }
}
```

**Effetto Diretto**:
```json
{
  "EventName": {
    "effect": "nome_effetto",
    "params": {
      "duration_ms": 2000,
      "color": [255, 128, 0],
      ...parametri specifici effetto
    },
    "priority": 1-10,
    "description": "Descrizione"
  }
}
```

### Priorità Effetti

- **10**: Critici (morte, scudi abbattuti)
- **8-9**: Importanti (salti FSD, combattimento)
- **5-7**: Normali (docking, scansioni)
- **1-4**: Minori (eventi di background)

Effetti con priorità più alta interrompono quelli con priorità più bassa.

## Uso Avanzato

### Controllo Manuale Dispositivi

```python
# Applica effetto a tutti i dispositivi
manager.apply_effect_to_all('pulse', {
    'duration_ms': 2000,
    'color': (255, 0, 0)
})

# Applica effetto solo a tastiere (2D)
manager.apply_effect_by_topology(
    TopologyType.MATRIX,
    'ripple',
    {'duration_ms': 3000, 'color': (0, 128, 255)}
)

# Applica effetto solo a RAM (1D)
manager.apply_effect_by_topology(
    TopologyType.LINEAR,
    'scanner',
    {'duration_ms': 2000, 'color': (255, 0, 0)}
)

# Applica effetto a dispositivo specifico
manager.apply_effect_to_device(
    'ASUS TUF Gaming K7',
    'explosion',
    {'duration_ms': 2000}
)
```

### Creare Temi Personalizzati

Modifica `unified_effect_manager.py` per aggiungere temi:

```python
def _get_theme_config(self, theme: str, event_data: Optional[dict] = None) -> dict:
    themes = {
        'my_custom_theme': {
            'matrix': {
                'effect': 'wave',
                'params': {
                    'duration_ms': 3000,
                    'color': (255, 0, 255),
                    'direction': 'horizontal'
                }
            },
            'linear': {
                'effect': 'chase',
                'params': {
                    'duration_ms': 3000,
                    'color': (255, 0, 255),
                    'spacing': 3,
                    'count': 4
                }
            }
        }
    }
    return themes.get(theme, ...)
```

### Informazioni sui Dispositivi

```python
# Lista tutti i dispositivi
devices = manager.get_device_list()
for dev in devices:
    print(f"{dev['name']}: {dev['topology']} - {dev['leds']} LEDs")

# Stampa riepilogo
manager.print_device_summary()
```

## Parametri Effetti

### Effetti 2D

#### Wave (Onda)
```python
{
    'duration_ms': 4000,
    'color': (255, 128, 0),
    'direction': 'horizontal',  # o 'vertical'
    'wavelength': 6.0
}
```

#### Ripple (Increspatura)
```python
{
    'duration_ms': 3000,
    'color': (0, 128, 255),
    'center': (3, 12)  # opzionale, default = centro
}
```

#### Explosion (Esplosione)
```python
{
    'duration_ms': 2000,
    'center': (3, 12)  # opzionale
}
```

### Effetti 1D

#### Scanner (Cylon)
```python
{
    'duration_ms': 2000,
    'color': (255, 0, 0),
    'width': 3.0,
    'tail_length': 5,
    'bounce': True
}
```

#### Chase (Inseguimento)
```python
{
    'duration_ms': 2000,
    'color': (0, 255, 128),
    'spacing': 3,
    'count': 3,
    'speed': 1.0
}
```

#### Fill (Riempimento)
```python
{
    'duration_ms': 2000,
    'color': (0, 255, 0),
    'direction': 'forward',  # o 'reverse'
    'reverse_at_end': False
}
```

#### Pulse (Pulsazione)
```python
{
    'duration_ms': 2000,
    'color': (255, 128, 0),
    'min_brightness': 0.1
}
```

#### Sparkle (Scintillio)
```python
{
    'duration_ms': 3000,
    'color': (255, 255, 255),
    'density': 0.2  # 0.0-1.0
}
```

## Script di Utilità

### Analizza Topologia Dispositivi
```bash
python analyze_keyboard.py
```
Mostra informazioni dettagliate sulla matrice LED di ogni dispositivo.

### Demo Effetti 2D
```bash
python demo_2d_effects.py
```
Demo completa effetti per tastiere (solo matrici 2D).

### Demo Sistema Unificato
```bash
python demo_unified_effects.py
```
Demo completa sistema multi-device.

## Troubleshooting

### Problema: Dispositivi non rilevati
**Soluzione**:
- Verifica che OpenRGB sia in esecuzione
- Abilita "SDK Server" nelle impostazioni di OpenRGB
- Riavvia OpenRGB e riprova

### Problema: Effetti non funzionano su alcuni dispositivi
**Soluzione**:
- Esegui `demo_unified_effects.py` per vedere quali dispositivi sono rilevati
- Alcuni dispositivi potrebbero non supportare il controllo individuale dei LED
- Verifica nella GUI di OpenRGB che il dispositivo funzioni correttamente

### Problema: Effetti troppo lenti o scattosi
**Soluzione**:
- Riduci il numero di dispositivi attivi
- Semplifica gli effetti (meno keyframes, durate più brevi)
- I dispositivi 1D sono più performanti dei 2D

### Problema: Effetti non si interrompono
**Soluzione**:
```python
# Stop tutti gli effetti
effect_manager.clear_all()

# O
event_processor.stop_all_effects()
```

## Best Practices

1. **Priorità**: Usa priorità alte (8-10) solo per eventi critici
2. **Durata**: Mantieni effetti sotto i 5 secondi per evitare sovrapposizioni
3. **Colori**: Usa colori coerenti per categorie di eventi (rosso = pericolo, blu = viaggio, verde = successo)
4. **Performance**: I dispositivi 1D possono gestire effetti più complessi delle tastiere 2D
5. **Test**: Testa sempre nuovi effetti con `demo_unified_effects.py` prima di usarli in gioco

## Esempi Configurazioni

### Configurazione Minimal (Solo Eventi Critici)
```json
{
  "UnderAttack": {"theme": "combat", "priority": 10},
  "ShieldState": {"theme": "shields_down", "priority": 9},
  "FSDJump": {"theme": "hyperspace", "priority": 8}
}
```

### Configurazione Completa (Tutti gli Eventi)
Vedi `config/unified_event_mappings_example.json`

### Configurazione Performance (Effetti Leggeri)
```json
{
  "FSDJump": {
    "effect": "pulse",
    "params": {"duration_ms": 1500, "color": [0, 128, 255]},
    "priority": 8
  },
  "UnderAttack": {
    "effect": "pulse",
    "params": {"duration_ms": 1000, "color": [255, 0, 0]},
    "priority": 10
  }
}
```

## Risorse

- **Documentazione OpenRGB**: https://openrgb.org/
- **Elite Dangerous Journal**: https://elite-journal.readthedocs.io/
- **Repository**: Vedi CLAUDE.md per dettagli architettura

## Supporto

Per problemi o domande:
1. Controlla questa guida e la sezione Troubleshooting
2. Verifica i log di OpenRGB
3. Testa con gli script demo per isolare il problema
