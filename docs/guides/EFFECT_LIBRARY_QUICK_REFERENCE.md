# Effect Library - Quick Reference

Quick lookup reference for the Visual Effects system.

---

## Base Effects Cheat Sheet

| Effect | Colors | Duration | Direction | Loop | Best For |
|--------|--------|----------|-----------|------|----------|
| **Static Transition** | 1 | ✓ | - | - | Fades, transitions |
| **Breath** | 2 | ✓ | - | ✓ | Pulsing, alerts |
| **Color Cycle** | 2+ | ✓ | ✓ | ✓ | Waves, rainbows |
| **Two Color Nuance** | 2 | ✓ | ✓ | - | Gradients |
| **Four Corner Nuance** | 4 | ✓ | - | - | Complex gradients (2D only) |
| **Explosion** | 5 | ✓ | - | ✓ | Ripples, impacts (2D only) |

---

## Common Effect Patterns

### Quick Fade
```
Type: Static Transition
Color: Target RGB
Duration: 500ms
```

### Breathing Effect
```
Type: Breath
Color 1: Bright color
Color 2: Black (0,0,0)
Duration: 2000ms
Loop: Yes
```

### Rainbow Wave
```
Type: Color Cycle
Colors: [Red, Orange, Yellow, Green, Blue, Purple]
Direction: right
Duration: 3000ms
Loop: Yes
```

### Alert Flash
```
Type: Breath
Color 1: Alert color (255,0,0)
Color 2: Black (0,0,0)
Duration: 500ms
Loop: Yes
```

---

## Elite Dangerous Color Themes

| Event Type | Primary Color | Secondary Color | Effect Type |
|------------|---------------|-----------------|-------------|
| **Hyperspace** | Blue (0,0,255) | White (255,255,255) | Explosion |
| **Combat** | Red (255,0,0) | Orange (255,128,0) | Breath |
| **Docked** | Green (0,255,0) | Dark Green (0,128,0) | Breath |
| **Shields Down** | Red (255,0,0) | Black (0,0,0) | Breath (fast) |
| **Discovery** | Cyan (0,255,255) | Blue (0,0,255) | Explosion |
| **Fuel Scoop** | Orange (255,128,0) | Yellow (255,255,0) | Gradient |

---

## Typical Durations

| Use Case | Duration Range |
|----------|----------------|
| Quick transition | 200-500ms |
| Normal effect | 1000-2000ms |
| Long effect | 2000-5000ms |
| Ambient/idle | Loop infinite |
| Alert | 500-1000ms looped |

---

## Priority Levels

| Priority | Use Case | Examples |
|----------|----------|----------|
| **10** | Critical alerts | Death, shields down |
| **8** | Important events | FSD jump, combat start |
| **5** | Normal events | Docking, trading |
| **3** | Low priority | Fuel scoop, scanning |
| **0** | Ambient | Idle mode, passive |

---

## Direction Values

### 2D Devices (Keyboards)
- `left` - Sweep from right to left
- `right` - Sweep from left to right
- `up` - Sweep from bottom to top
- `down` - Sweep from top to bottom
- `tl` - Diagonal from bottom-right to top-left
- `tr` - Diagonal from bottom-left to top-right
- `bl` - Diagonal from top-right to bottom-left
- `br` - Diagonal from top-left to bottom-right

### 1D Devices (LED Strips)
- `left` / `horizontal` - Left to right
- `right` - Right to left

---

## JSON Template

### Minimal Visual Effect
```json
{
  "id": "my_effect",
  "name": "My Effect",
  "description": "What it does",
  "steps": [
    {
      "step_id": 0,
      "effect_type": "static_transition",
      "params": {
        "colors": [[255, 0, 0]],
        "duration_ms": 1000,
        "loop_infinite": false
      }
    }
  ],
  "topology_support": ["2D", "1D"],
  "post_behavior": "turn_off",
  "category": "custom"
}
```

### Multi-Step Effect
```json
{
  "id": "hyperspace",
  "name": "Hyperspace Jump",
  "description": "FSD jump sequence",
  "steps": [
    {
      "step_id": 0,
      "effect_type": "static_transition",
      "params": {
        "colors": [[0, 0, 255]],
        "duration_ms": 500,
        "loop_infinite": false
      }
    },
    {
      "step_id": 1,
      "effect_type": "explosion",
      "params": {
        "colors": [
          [0, 50, 255],
          [0, 150, 255],
          [100, 200, 255],
          [200, 220, 255],
          [255, 255, 255]
        ],
        "duration_ms": 1200,
        "num_loops": 1,
        "loop_infinite": false
      }
    },
    {
      "step_id": 2,
      "effect_type": "breath",
      "params": {
        "colors": [[255, 255, 255], [0, 0, 0]],
        "duration_ms": 2000,
        "loop_infinite": false
      }
    }
  ],
  "topology_support": ["2D", "1D"],
  "post_behavior": "turn_off",
  "category": "predefined"
}
```

---

## Python API Quick Reference

### Load Library
```python
from core.visual_effect_library import VisualEffectLibrary

library = VisualEffectLibrary()
effects = library.get_all_effects()
effect = library.get_effect("hyperspace_jump")
```

### Create Effect
```python
from core.base_effects import *

effect = VisualEffect(
    id="my_effect",
    name="My Effect",
    description="Description",
    steps=[
        BaseEffectStep(
            step_id=0,
            effect_type=BaseEffectType.STATIC_TRANSITION,
            params=BaseEffectParams(
                colors=[(255, 0, 0)],
                duration_ms=1000
            )
        )
    ],
    topology_support=["2D", "1D"],
    post_behavior=PostSequenceBehavior.TURN_OFF,
    category="custom"
)

library.add_effect(effect)
library.save_all()
```

### Play Effect
```python
from effects.unified_manager import UnifiedEffectManager
from openrgb import OpenRGBClient

client = OpenRGBClient("localhost", 6742)
manager = UnifiedEffectManager(client)

# Play on all devices
manager.play_visual_effect("hyperspace_jump", blocking=False)

# Play on specific device
keyboard = manager.get_device_by_name("keyboard")
manager.play_visual_effect("combat_alert", devices=[keyboard])
```

### Render to Simulator
```python
from core.visual_effect_renderer import VisualEffectRenderer

renderer = VisualEffectRenderer()

renderer.start_effect(
    device_id="simulator",
    device_controller=mock_device,
    visual_effect=effect,
    simulator_mode=True,
    blocking=False
)
```

---

## Keyboard Shortcuts (UI)

| Action | Shortcut |
|--------|----------|
| New Effect | Ctrl+N |
| Save Effect | Ctrl+S |
| Test Sequence | F5 |
| Test Hardware | F6 |
| Stop Test | Esc |
| Copy Step | Ctrl+C |
| Paste Step | Ctrl+V |
| Delete Step | Del |

*(Note: Shortcuts may vary by implementation)*

---

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Effect won't save | Check file permissions on `config/` folder |
| Simulator not updating | Click "Stop Test" then try again |
| Hardware not responding | Verify OpenRGB is running, click "Reconnect" |
| Colors look wrong | Check RGB values are 0-255, not 0.0-1.0 |
| Effect too fast/slow | Adjust `duration_ms` parameters |
| Effect won't play | Check topology support matches device |

---

## File Locations

```
config/
├── visual_effects.json       # Visual Effects library
├── color_schemes.json         # Color Schemes library
└── event_mappings.json     # Event-to-effect mappings

src_integrated/
├── core/
│   ├── base_effects.py              # Data models
│   ├── visual_effect_library.py     # Library management
│   ├── visual_effect_renderer.py    # Rendering engine
│   └── color_scheme_library.py      # Color schemes
├── effects/
│   ├── pulse_2d.py                  # Pulse/fade effects
│   ├── gradient_2d.py               # 2-color gradients
│   ├── corner_gradient_2d.py        # 4-corner gradients
│   └── unified_manager.py           # Device manager
└── ui/
    ├── effect_library_tab.py        # Main editor
    └── keyboard_matrix_simulator.py # Simulator widget
```

---

## Testing Commands

```bash
# Test core functionality
cd src_integrated
python test_effect_library.py

# Test GUI simulator
python test_simulator_gui.py

# Run application
python main.py
```

---

## Common Game Event IDs

| Event | ID | Typical Effect |
|-------|----|----|
| FSD Jump | `FSDJump` | Hyperspace explosion |
| Docked | `Docked` | Green safe transition |
| Undocked | `Undocked` | Quick flash |
| Under Attack | `UnderAttack` | Red pulse |
| Hull Damage | `HullDamage` | Orange flash |
| Shield State | `ShieldState` | Red alert (shields down) |
| Supercruise Entry | `SupercruiseEntry` | Blue fade |
| Fuel Scoop | `FuelScoop` | Orange gradient |
| Discovery | `FSSDiscoveryScan` | Cyan explosion |
| Scan Complete | `SAAScanComplete` | Blue flash |

---

## RGB Color Reference

### Common Colors
```
Red:         (255, 0, 0)
Orange:      (255, 128, 0)
Yellow:      (255, 255, 0)
Green:       (0, 255, 0)
Cyan:        (0, 255, 255)
Blue:        (0, 0, 255)
Purple:      (128, 0, 255)
Magenta:     (255, 0, 255)
White:       (255, 255, 255)
Black:       (0, 0, 0)
```

### Elite Dangerous Palette
```
ED Blue:     (0, 0, 255)
ED Orange:   (255, 128, 0)
ED Green:    (0, 255, 0)
ED Cyan:     (0, 255, 255)
UI Orange:   (255, 165, 0)
Alert Red:   (255, 0, 0)
Safe Green:  (0, 200, 0)
```

---

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Simulator FPS | 30 | 30-60 |
| Hardware FPS | 30 | 20-40 |
| Effect Load Time | <100ms | ~50ms |
| Library Load Time | <500ms | ~200ms |
| Max Concurrent Effects | 5 | 3-5 |

---

## Support Links

- **User Guide**: `EFFECT_LIBRARY_USER_GUIDE.md`
- **Developer Guide**: `EFFECT_LIBRARY_DEVELOPER_GUIDE.md`
- **Journal Events**: `JOURNAL_EVENTS_REFERENCE.md`
- **GitHub Issues**: Report bugs and request features

---

*Quick Reference v2.0 | Last Updated: 2025-12-18*
