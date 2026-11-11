# Guida agli Effetti 2D per Tastiera

## Panoramica

Il sistema di effetti 2D ti permette di creare animazioni spaziali sulla tua tastiera ASUS TUF Gaming K7 (105 LED indirizzabili individualmente).

## Struttura della Tastiera

- **Matrice**: 6 righe × 24 colonne
- **LED totali**: 105
- **Controllo**: Ogni LED può essere indirizzato singolarmente

## Come Eseguire la Demo

```bash
python demo_2d_effects.py
```

Questo script mostrerà tutti gli effetti 2D disponibili in sequenza.

## Effetti Disponibili

### 1. Horizontal Sweep
Linea orizzontale che scorre dall'alto verso il basso (o viceversa).

```python
from src.effects.animated_2d_effects import HorizontalSweepEffect

effect = HorizontalSweepEffect(
    matrix,
    duration_ms=2000,
    color=(255, 128, 0),      # Arancione
    direction='down',          # 'down' o 'up'
    trail_length=3             # Lunghezza scia
)
effect.start(blocking=True)
```

### 2. Vertical Sweep
Linea verticale che scorre da sinistra a destra (o viceversa).

```python
from src.effects.animated_2d_effects import VerticalSweepEffect

effect = VerticalSweepEffect(
    matrix,
    duration_ms=2000,
    color=(0, 255, 128),
    direction='right',         # 'right' o 'left'
    trail_length=3
)
effect.start(blocking=True)
```

### 3. Ripple (Increspatura)
Cerchio che si espande dal centro (o da un punto specifico).

```python
from src.effects.animated_2d_effects import RippleEffect

effect = RippleEffect(
    matrix,
    duration_ms=3000,
    color=(0, 128, 255),
    center=(3, 12)             # Opzionale, default = centro tastiera
)
effect.start(blocking=True)
```

### 4. Wave (Onda)
Onda sinusoidale che attraversa la tastiera.

```python
from src.effects.animated_2d_effects import WaveEffect

effect = WaveEffect(
    matrix,
    duration_ms=4000,
    color=(255, 0, 255),
    direction='horizontal',    # 'horizontal' o 'vertical'
    wavelength=6.0             # Lunghezza d'onda
)
effect.start(blocking=True)
```

### 5. Explosion (Esplosione)
Effetto esplosione con transizione di colori (bianco → giallo → arancione → rosso → nero).

```python
from src.effects.animated_2d_effects import ExplosionEffect

effect = ExplosionEffect(
    matrix,
    duration_ms=2000,
    center=(3, 12)             # Opzionale
)
effect.start(blocking=True)
```

### 6. Imploding Circles (Cerchi Implosivi)
Cerchi concentrici che si restringono verso il centro.

```python
from src.effects.animated_2d_effects import ImplodingCirclesEffect

effect = ImplodingCirclesEffect(
    matrix,
    duration_ms=3000,
    color=(0, 255, 128),
    center=(3, 12),            # Opzionale
    num_circles=6              # Numero di cerchi
)
effect.start(blocking=True)
```

### 7. Diagonal Sweep (Scansione Diagonale)
Linea diagonale che attraversa la tastiera.

```python
from src.effects.animated_2d_effects import DiagonalSweepEffect

effect = DiagonalSweepEffect(
    matrix,
    duration_ms=2000,
    color=(255, 255, 0),
    direction=1                # 1 = TL→BR, -1 = TR→BL
)
effect.start(blocking=True)
```

## Pattern Statici

Puoi anche creare pattern statici senza animazione:

### Linea Orizzontale
```python
color_map = matrix.generate_horizontal_line(row=2, color=(255, 0, 0))
matrix.apply_color_map(color_map)
```

### Linea Verticale
```python
color_map = matrix.generate_vertical_line(col=10, color=(0, 255, 0))
matrix.apply_color_map(color_map)
```

### Cerchio
```python
color_map = matrix.generate_circle(
    center=(3, 12),
    radius=5.0,
    color=(0, 0, 255),
    thickness=0.5
)
matrix.apply_color_map(color_map)
```

### Cerchio Pieno
```python
color_map = matrix.generate_filled_circle(
    center=(3, 12),
    radius=5.0,
    color=(255, 128, 0)
)
matrix.apply_color_map(color_map)
```

### Gradiente
```python
# Orizzontale
color_map = matrix.generate_gradient(
    direction='horizontal',
    color1=(255, 0, 0),        # Rosso
    color2=(0, 0, 255)         # Blu
)
matrix.apply_color_map(color_map)

# Verticale
color_map = matrix.generate_gradient(direction='vertical', ...)

# Radiale (dal centro)
color_map = matrix.generate_gradient(direction='radial', ...)
```

## Integrazione con Eventi Elite Dangerous

Puoi mappare questi effetti agli eventi del gioco:

```python
# Esempio: Esplosione quando scudi scendono
if event == "ShieldDown":
    effect = ExplosionEffect(matrix, duration_ms=1500)
    effect.start()

# Esempio: Ripple quando si entra in supercruise
if event == "SupercruiseEntry":
    effect = RippleEffect(matrix, duration_ms=2000, color=(0, 128, 255))
    effect.start()

# Esempio: Onda durante FSD jump
if event == "FSDJump":
    effect = WaveEffect(matrix, duration_ms=3000, color=(255, 255, 255))
    effect.start()
```

## Creare Effetti Personalizzati

Puoi creare i tuoi effetti personalizzati estendendo `Animated2DEffect`:

```python
from src.effects.animated_2d_effects import Animated2DEffect

class MyCustomEffect(Animated2DEffect):
    def __init__(self, matrix, duration_ms=2000):
        super().__init__(matrix, duration_ms)

    def render_frame(self, time_ms: int):
        # Il tuo codice qui
        progress = time_ms / self.duration_ms

        # Genera color_map basato su progress
        color_map = {}
        for row, col, led_idx in self.matrix.get_all_led_coords():
            # Calcola colore per questo LED
            color = calculate_color(row, col, progress)
            color_map[led_idx] = color

        self.matrix.apply_color_map(color_map)
```

## Setup Base

```python
from openrgb import OpenRGBClient
from openrgb.utils import DeviceType
from src.effects.keyboard_matrix_2d import KeyboardMatrix2D

# Connetti a OpenRGB
client = OpenRGBClient()

# Trova la tastiera
keyboard = None
for device in client.devices:
    if device.type == DeviceType.KEYBOARD:
        keyboard = device
        break

# Crea oggetto matrice
matrix_map = keyboard.zones[0].matrix_map
matrix = KeyboardMatrix2D(matrix_map, keyboard)

# Ora puoi usare matrix con qualsiasi effetto!
```

## Note Tecniche

- **FPS**: Gli effetti animati girano a 30 FPS di default
- **Threading**: Gli effetti possono girare in background (`blocking=False`)
- **Performance**: Gli effetti sono ottimizzati per non sovraccaricare il sistema
- **Coordinate**: (0,0) = angolo in alto a sinistra, (5,23) = angolo in basso a destra

## Requisiti

- OpenRGB in esecuzione con SDK Server abilitato
- Tastiera con matrice LED 2D (testato su ASUS TUF Gaming K7)
- Python 3.11+
- openrgb-python library

## Troubleshooting

**Problema**: "No keyboard found"
- Soluzione: Verifica che OpenRGB sia in esecuzione e la tastiera sia rilevata

**Problema**: "Keyboard does not have matrix map"
- Soluzione: Non tutte le tastiere espongono la matrix map. Verifica con `analyze_keyboard.py`

**Problema**: Effetti lenti o scattosi
- Soluzione: Riduci FPS o semplifica l'effetto

**Problema**: Alcuni LED non si accendono
- Soluzione: Controlla che i LED funzionino in OpenRGB, potrebbero essere mappati come `None` nella matrice
