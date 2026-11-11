# Effect Library - Developer Guide

## Overview

This guide provides technical documentation for developers working with or extending the Effect Library system in ED:Event2Led.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Data Models](#data-models)
4. [File Formats](#file-formats)
5. [Rendering Pipeline](#rendering-pipeline)
6. [API Reference](#api-reference)
7. [Extending the System](#extending-the-system)
8. [Testing](#testing)

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────────┐
│  UI Layer (PyQt6)                                       │
│  - EffectLibraryTab                                     │
│  - KeyboardMatrixSimulator                              │
│  - EventMapperTab                                       │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Core Logic Layer                                       │
│  - VisualEffectLibrary (manages effects)                │
│  - VisualEffectRenderer (renders sequences)             │
│  - ColorSchemeLibrary (manages color schemes)           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Effects Layer                                          │
│  - Base Effects (Static, Breath, Cycle, etc.)          │
│  - Spatial Effects 2D (Matrix-based animations)         │
│  - Spatial Effects 1D (Linear animations)               │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Device Layer                                           │
│  - UnifiedEffectManager (device management)             │
│  - DeviceEffectController (per-device wrapper)          │
│  - OpenRGBClient (hardware communication)               │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: UI, logic, and hardware layers are decoupled
2. **Composition over Inheritance**: Visual Effects compose Base Effects
3. **Topology Abstraction**: Effects adapt to 2D/1D/0D device layouts
4. **Dual System**: New Visual Effects coexist with legacy Fused Effects

---

## Core Components

### File Structure

```
src_integrated/
├── core/
│   ├── base_effects.py              # Data models
│   ├── visual_effect_library.py     # Library management
│   ├── visual_effect_renderer.py    # Rendering engine
│   ├── color_scheme_library.py      # Color schemes
│   ├── fused_effect.py              # Legacy system
│   └── effect_renderer.py           # Legacy renderer
├── effects/
│   ├── device_topology.py           # Topology detection
│   ├── keyboard_matrix_2d.py        # 2D controller
│   ├── linear_1d.py                 # 1D controller
│   ├── pulse_2d.py                  # Pulse/Fade effects
│   ├── gradient_2d.py               # 2-color gradient
│   ├── corner_gradient_2d.py        # 4-corner gradient
│   ├── spatial_effects_2d.py        # Matrix animations
│   ├── spatial_effects_1d.py        # Linear animations
│   └── unified_manager.py           # Device management
├── ui/
│   ├── effect_library_tab.py        # Main editor UI
│   ├── keyboard_matrix_simulator.py # Visual simulator
│   ├── event_mapper_tab.py          # Event mapping
│   └── device_test_tab.py           # Device testing
└── config/
    ├── visual_effects.json          # Visual Effects library
    ├── color_schemes.json           # Color Schemes library
    └── event_mappings.json       # Event mappings
```

---

## Data Models

### Base Effect Types

```python
from enum import Enum

class BaseEffectType(Enum):
    STATIC_TRANSITION = "static_transition"
    BREATH = "breath"
    COLOR_CYCLE = "color_cycle"
    TWO_COLOR_NUANCE = "two_color_nuance"
    FOUR_CORNER_NUANCE = "four_corner_nuance"
    EXPLOSION = "explosion"
```

### Base Effect Parameters

```python
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class BaseEffectParams:
    """Parameters for a base effect."""
    colors: List[Tuple[int, int, int]]  # RGB tuples (0-255)
    duration_ms: int                     # Duration in milliseconds
    direction: Optional[str] = None      # Direction for spatial effects
    speed: Optional[float] = None        # Speed multiplier (unused currently)
    num_loops: Optional[int] = None      # Number of loops for explosion
    loop_infinite: bool = False          # Loop this step forever
```

**Fields**:
- `colors`: List of RGB color tuples. Length varies by effect type:
  - Static Transition: 1 color
  - Breath: 2 colors
  - Color Cycle: 2+ colors
  - Two Color Nuance: 2 colors
  - Four Corner Nuance: 4 colors
  - Explosion: 5 colors (inner to outer gradient)

- `duration_ms`: Effect duration in milliseconds (positive integer)

- `direction`: Spatial direction string (for spatial effects):
  - 2D: `"left"`, `"right"`, `"up"`, `"down"`, `"tl"`, `"tr"`, `"bl"`, `"br"`
  - 1D: `"left"`, `"right"` (or `"horizontal"`)

- `loop_infinite`: If `True`, effect repeats indefinitely (sequence doesn't advance)

### Base Effect Step

```python
@dataclass
class BaseEffectStep:
    """A single step in a visual effect sequence."""
    step_id: int                 # Unique ID within effect (0, 1, 2, ...)
    effect_type: BaseEffectType  # Type of base effect
    params: BaseEffectParams     # Effect parameters
```

### Post-Sequence Behavior

```python
class PostSequenceBehavior(Enum):
    TURN_OFF = "turn_off"              # LEDs go black
    STATIC_COLOR = "static_color"      # Hold a color
    LOOP_EFFECT = "loop_effect"        # Repeat a step
    COLOR_SCHEME = "color_scheme"      # Apply color scheme
```

### Visual Effect

```python
@dataclass
class VisualEffect:
    """A complete visual effect (sequence of base effects)."""
    id: str                              # Unique identifier
    name: str                            # Display name
    description: str                     # User description
    steps: List[BaseEffectStep]          # Ordered sequence
    topology_support: List[str]          # ["2D"], ["1D"], ["0D"], or combinations
    post_behavior: PostSequenceBehavior  # What happens after sequence
    post_behavior_data: Optional[Dict[str, Any]] = None  # Data for post_behavior
    category: str = "custom"             # "predefined" or "custom"

    def supports_topology(self, topology: str) -> bool:
        """Check if effect supports a device topology."""
        return topology in self.topology_support

    def total_duration_ms(self) -> int:
        """Calculate total duration of all non-infinite steps."""
        return sum(
            step.params.duration_ms
            for step in self.steps
            if not step.params.loop_infinite
        )
```

### Color Scheme

```python
@dataclass
class ColorScheme:
    """LED-by-LED color configuration for keyboards."""
    id: str                                      # Unique identifier
    name: str                                    # Display name
    description: str                             # User description
    device_type: str = "keyboard"                # Target device type
    led_colors: Dict[int, Tuple[int, int, int]]  # led_index -> RGB
    key_bindings: Optional[Dict[str, int]] = None  # ED key name -> led_index
```

---

## File Formats

### Visual Effects JSON

**Location**: `config/visual_effects.json`

**Schema**:
```json
{
  "version": 1,
  "effects": [
    {
      "id": "hyperspace_jump",
      "name": "Hyperspace Jump",
      "description": "Blue transition followed by white explosion",
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
        }
      ],
      "topology_support": ["2D", "1D"],
      "post_behavior": "turn_off",
      "post_behavior_data": null,
      "category": "predefined"
    }
  ]
}
```

**Field Descriptions**:
- `version`: Schema version (currently 1)
- `effects`: Array of Visual Effect objects
- `id`: Must be unique across all effects
- `effect_type`: One of 6 base effect type strings
- `colors`: Array of RGB arrays (each RGB is [R, G, B] with 0-255 values)
- `topology_support`: Array of strings: `"2D"`, `"1D"`, `"0D"`
- `post_behavior`: One of `"turn_off"`, `"static_color"`, `"loop_effect"`, `"color_scheme"`

### Color Schemes JSON

**Location**: `config/color_schemes.json`

**Schema**:
```json
{
  "version": 1,
  "schemes": [
    {
      "id": "ed_combat",
      "name": "Elite Dangerous Combat Keys",
      "description": "Combat key bindings",
      "device_type": "keyboard",
      "led_colors": {
        "0": [255, 0, 0],
        "1": [255, 128, 0],
        "2": [255, 255, 0]
      },
      "key_bindings": {
        "PrimaryFire": 0,
        "SecondaryFire": 1,
        "DeployHardpoints": 2
      }
    }
  ]
}
```

**Field Descriptions**:
- `led_colors`: Map of LED index (string) to RGB array
- `key_bindings`: Optional map of Elite Dangerous key names to LED indices

### Event Mappings JSON (v2)

**Location**: `config/event_mappings.json`

**Schema**:
```json
{
  "version": 2,
  "mappings": {
    "FSDJump": {
      "effect_type": "visual",
      "effect_id": "hyperspace_jump",
      "priority": 8,
      "enabled": true
    },
    "Docked": {
      "effect_type": "visual",
      "effect_id": "docked_safe",
      "priority": 5,
      "enabled": true
    },
    "UnderAttack": {
      "effect_type": "fused",
      "effect_id": "combat_pulse",
      "priority": 10,
      "enabled": true
    }
  }
}
```

**Field Descriptions**:
- `effect_type`: `"fused"` (legacy), `"visual"` (new), or `"color_scheme"`
- `effect_id`: ID of effect in respective library
- `priority`: 0-10 (higher = more important)
- `enabled`: Boolean flag

**Backward Compatibility**: If `effect_type` is missing, defaults to `"fused"`.

---

## Rendering Pipeline

### Visual Effect Renderer Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VisualEffectRenderer.start_effect()                      │
│    - Receive Visual Effect + Device Controller              │
│    - Validate topology compatibility                        │
│    - Start rendering thread                                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. For each BaseEffectStep in sequence:                     │
│    - Map step to spatial effect class                       │
│    - Create spatial effect instance                         │
│    - Start spatial effect animation                         │
│    - Wait for duration_ms                                   │
│    - If loop_infinite=True, stay on this step               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Apply post_behavior:                                     │
│    - TURN_OFF: Set all LEDs to black                        │
│    - STATIC_COLOR: Set all LEDs to specified color          │
│    - LOOP_EFFECT: Restart specified step                    │
│    - COLOR_SCHEME: Apply saved color scheme                 │
└─────────────────────────────────────────────────────────────┘
```

### Base Effect to Spatial Effect Mapping

**2D Devices (Keyboards)**:

| Base Effect          | Spatial Effect Class      | Implementation                |
|----------------------|---------------------------|-------------------------------|
| Static Transition    | FadeEffect2D              | Uniform fade to target color  |
| Breath               | PulseEffect2D             | Oscillating brightness        |
| Color Cycle          | WaveEffect                | N-color wave movement         |
| Two Color Nuance     | GradientEffect2D          | Linear gradient               |
| Four Corner Nuance   | CornerGradientEffect2D    | Bilinear interpolation        |
| Explosion            | ExplosionEffect           | Concentric expanding circles  |

**1D Devices (LED Strips, RAM)**:

| Base Effect          | Spatial Effect Class      | Implementation                |
|----------------------|---------------------------|-------------------------------|
| Static Transition    | FadeEffect1D              | Uniform fade                  |
| Breath               | PulseEffect1D             | Oscillating brightness        |
| Color Cycle          | WaveEffect1D              | N-color wave                  |
| Two Color Nuance     | GradientShiftEffect1D     | Linear gradient               |
| Four Corner Nuance   | GradientShiftEffect1D     | Fallback to 2-color gradient  |
| Explosion            | CenterOutEffect1D         | Center-out wave               |

### Rendering Thread Safety

- Each effect runs in its own daemon thread
- Spatial effects use threading locks for LED updates
- Device controllers serialize hardware writes
- Simulator updates use Qt signals for thread safety

---

## API Reference

### VisualEffectLibrary

**Location**: `src_integrated/core/visual_effect_library.py`

```python
class VisualEffectLibrary:
    def __init__(self, effects_file: str = "config/visual_effects.json"):
        """Initialize library and load effects from file."""

    def get_effect(self, effect_id: str) -> Optional[VisualEffect]:
        """Get effect by ID."""

    def get_all_effects(self) -> List[VisualEffect]:
        """Get all effects as list."""

    def add_effect(self, effect: VisualEffect) -> bool:
        """Add new effect to library."""

    def update_effect(self, effect: VisualEffect) -> bool:
        """Update existing effect."""

    def delete_effect(self, effect_id: str) -> bool:
        """Delete effect from library."""

    def save_all(self) -> bool:
        """Save library to JSON file."""

    def load_all(self):
        """Load effects from JSON file."""

    def import_effect(self, file_path: str) -> bool:
        """Import effect from external JSON file."""

    def export_effect(self, effect_id: str, file_path: str) -> bool:
        """Export effect to external JSON file."""
```

**Usage Example**:
```python
from core.visual_effect_library import VisualEffectLibrary

# Load library
library = VisualEffectLibrary()

# Get effect
effect = library.get_effect("hyperspace_jump")

# Create new effect
from core.base_effects import VisualEffect, BaseEffectStep, BaseEffectType, BaseEffectParams, PostSequenceBehavior

new_effect = VisualEffect(
    id="my_custom_effect",
    name="My Custom Effect",
    description="A custom lighting effect",
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

library.add_effect(new_effect)
library.save_all()
```

### VisualEffectRenderer

**Location**: `src_integrated/core/visual_effect_renderer.py`

```python
class VisualEffectRenderer:
    def start_effect(
        self,
        device_id: str,
        device_controller,
        visual_effect: VisualEffect,
        simulator_mode: bool = False,
        blocking: bool = False
    ):
        """
        Start rendering a visual effect.

        Args:
            device_id: Unique device identifier
            device_controller: DeviceEffectController instance
            visual_effect: VisualEffect to render
            simulator_mode: If True, render to simulator instead of hardware
            blocking: If True, wait for effect to complete
        """

    def stop_all(self):
        """Stop all active effects."""

    def stop_device(self, device_id: str):
        """Stop effects on specific device."""
```

**Usage Example**:
```python
from core.visual_effect_renderer import VisualEffectRenderer

renderer = VisualEffectRenderer()

# Render on hardware
renderer.start_effect(
    device_id="keyboard_0",
    device_controller=device_ctrl,
    visual_effect=effect,
    simulator_mode=False,
    blocking=False
)

# Stop all
renderer.stop_all()
```

### UnifiedEffectManager

**Location**: `src_integrated/effects/unified_manager.py`

```python
class UnifiedEffectManager:
    def play_visual_effect(
        self,
        effect_id: str,
        devices: Optional[List[DeviceEffectController]] = None,
        blocking: bool = False
    ):
        """
        Play visual effect on specified devices.

        Args:
            effect_id: ID of effect in visual library
            devices: List of devices (None = all devices)
            blocking: Wait for effect completion
        """

    def apply_color_scheme(
        self,
        scheme_id: str,
        devices: Optional[List[DeviceEffectController]] = None
    ):
        """
        Apply color scheme to devices.

        Args:
            scheme_id: ID of scheme in color scheme library
            devices: List of devices (None = all keyboards)
        """

    def reload_visual_library(self):
        """Reload visual effects from disk."""

    def reload_color_schemes(self):
        """Reload color schemes from disk."""
```

**Usage Example**:
```python
from openrgb import OpenRGBClient
from effects.unified_manager import UnifiedEffectManager

# Connect to OpenRGB
client = OpenRGBClient("localhost", 6742)
manager = UnifiedEffectManager(client)

# Play visual effect on all devices
manager.play_visual_effect("hyperspace_jump", blocking=False)

# Play on specific device
keyboard = manager.get_device_by_name("keyboard")
if keyboard:
    manager.play_visual_effect("combat_alert", devices=[keyboard])

# Apply color scheme
manager.apply_color_scheme("ed_combat")
```

---

## Extending the System

### Adding a New Base Effect Type

1. **Add enum value** in `core/base_effects.py`:
```python
class BaseEffectType(Enum):
    # ... existing types ...
    MY_NEW_EFFECT = "my_new_effect"
```

2. **Create spatial effect classes**:

**2D version** (`effects/my_effect_2d.py`):
```python
from effects.spatial_effects_2d import Animated2DEffect

class MyEffect2D(Animated2DEffect):
    def __init__(self, matrix, duration_ms, color, **kwargs):
        super().__init__(matrix, duration_ms)
        self.color = color

    def render_frame(self, time_ms: int):
        """Called every frame at 30 FPS."""
        progress = time_ms / self.duration_ms  # 0.0 to 1.0

        # Implement your animation logic here
        for row in range(self.matrix.rows):
            for col in range(self.matrix.cols):
                # Calculate color based on position and progress
                r, g, b = self.color
                self.matrix.set_led(row, col, (r, g, b))
```

**1D version** (`effects/my_effect_1d.py`):
```python
from effects.spatial_effects_1d import Animated1DEffect

class MyEffect1D(Animated1DEffect):
    def __init__(self, controller, duration_ms, color, **kwargs):
        super().__init__(controller, duration_ms)
        self.color = color

    def render_frame(self, time_ms: int):
        """Called every frame at 30 FPS."""
        progress = time_ms / self.duration_ms

        for i in range(self.controller.led_count):
            # Calculate color for this LED
            r, g, b = self.color
            self.controller.set_led(i, (r, g, b))
```

3. **Map in renderer** (`core/visual_effect_renderer.py`):
```python
def _create_2d_effect(self, device_controller, effect_type, params):
    # ... existing mappings ...
    elif effect_type == BaseEffectType.MY_NEW_EFFECT:
        from effects.my_effect_2d import MyEffect2D
        return MyEffect2D(
            matrix,
            duration_ms,
            color=params.colors[0]
        )

def _create_1d_effect(self, device_controller, effect_type, params):
    # ... existing mappings ...
    elif effect_type == BaseEffectType.MY_NEW_EFFECT:
        from effects.my_effect_1d import MyEffect1D
        return MyEffect1D(
            controller,
            duration_ms,
            color=params.colors[0]
        )
```

4. **Update UI** (`ui/effect_library_tab.py`):

Add new effect type to dropdown in step parameter editor (implementation depends on your UI design).

### Creating Custom Predefined Effects

Add to `visual_effect_library.py` in `_create_predefined_effects()`:

```python
def _create_predefined_effects(self) -> List[VisualEffect]:
    effects = []

    # ... existing predefined effects ...

    # Your custom effect
    my_effect = VisualEffect(
        id="my_predefined_effect",
        name="My Predefined Effect",
        description="Description of what it does",
        steps=[
            BaseEffectStep(
                step_id=0,
                effect_type=BaseEffectType.STATIC_TRANSITION,
                params=BaseEffectParams(
                    colors=[(255, 0, 0)],
                    duration_ms=500
                )
            ),
            # ... more steps ...
        ],
        topology_support=["2D", "1D"],
        post_behavior=PostSequenceBehavior.TURN_OFF,
        category="predefined"
    )
    effects.append(my_effect)

    return effects
```

### Adding Device Topology Support

If you need a new topology type (e.g., "3D" for volumetric displays):

1. **Add topology type** in `effects/device_topology.py`:
```python
class TopologyType(Enum):
    # ... existing types ...
    VOLUMETRIC = "volumetric"
```

2. **Update detection** in `TopologyDetector.detect()`:
```python
def detect(self, device) -> DeviceTopology:
    # ... existing detection logic ...

    if self._is_volumetric(device):
        return self._detect_volumetric(device)
```

3. **Create controller** in `effects/` (e.g., `volumetric_3d.py`):
```python
class Volumetric3D:
    def __init__(self, device, depth, rows, cols):
        self.device = device
        self.depth = depth
        self.rows = rows
        self.cols = cols

    def set_voxel(self, z, y, x, color):
        """Set color at 3D coordinate."""
        led_index = z * (rows * cols) + y * cols + x
        self.device.leds[led_index].set_color(color)
```

---

## Testing

### Unit Testing

**Test Core Models**:
```python
# test_base_effects.py
from core.base_effects import VisualEffect, BaseEffectStep, BaseEffectType, BaseEffectParams

def test_visual_effect_creation():
    effect = VisualEffect(
        id="test",
        name="Test",
        description="Test effect",
        steps=[],
        topology_support=["2D"],
        post_behavior=PostSequenceBehavior.TURN_OFF
    )
    assert effect.id == "test"
    assert effect.supports_topology("2D")
    assert not effect.supports_topology("1D")

def test_total_duration():
    effect = VisualEffect(
        id="test",
        name="Test",
        description="Test",
        steps=[
            BaseEffectStep(0, BaseEffectType.STATIC_TRANSITION,
                          BaseEffectParams(colors=[(255,0,0)], duration_ms=1000)),
            BaseEffectStep(1, BaseEffectType.BREATH,
                          BaseEffectParams(colors=[(0,255,0),(0,0,0)], duration_ms=2000))
        ],
        topology_support=["2D"],
        post_behavior=PostSequenceBehavior.TURN_OFF
    )
    assert effect.total_duration_ms() == 3000
```

### Integration Testing

Use the provided test scripts:

```bash
# Test core functionality
python src_integrated/test_effect_library.py

# Test GUI simulator
python src_integrated/test_simulator_gui.py
```

### Manual Testing Checklist

**Effect Creation**:
- [ ] Create new effect
- [ ] Add 3+ steps with different base effects
- [ ] Save effect
- [ ] Reload application - effect persists
- [ ] Clone effect - creates copy with new ID
- [ ] Delete effect - removes from library

**Simulator Testing**:
- [ ] Test single step preview
- [ ] Test full sequence preview
- [ ] Visual output matches expectations
- [ ] Simulator runs at 30+ FPS

**Hardware Testing**:
- [ ] Connect OpenRGB
- [ ] Test effect on actual hardware
- [ ] Effect plays on all compatible devices
- [ ] Effect respects topology support

**Event Mapping**:
- [ ] Map effect to game event
- [ ] Test mapping from Events tab
- [ ] Effect triggers correctly during gameplay
- [ ] Priority system works (high priority interrupts low)

---

## Performance Considerations

### Frame Rate

- **Target**: 30 FPS for smooth animation
- **Actual**: 30-60 FPS on modern hardware
- **Bottleneck**: Hardware write latency (OpenRGB communication)

### Memory Usage

- **Visual Effect**: ~1 KB per effect
- **Library**: ~5-10 KB for typical library (50 effects)
- **Renderer**: ~100 KB per active rendering thread
- **Simulator**: ~500 KB for 6×22 matrix display

### Threading Model

- **Main Thread**: UI updates (PyQt6 event loop)
- **Rendering Threads**: One per active effect (daemon threads)
- **OpenRGB Thread**: Hardware communication (blocking I/O)

**Best Practices**:
- Keep effects under 5 seconds to avoid queue buildup
- Limit concurrent effects to 3-5 for optimal performance
- Use simulator for rapid testing to reduce hardware wear

---

## Troubleshooting

### Common Issues

**Issue**: Effects not saving
- **Cause**: Permission error writing to `config/` directory
- **Fix**: Run with appropriate permissions or change config path

**Issue**: Simulator not updating
- **Cause**: Threading issue or QPaintEvent not triggering
- **Fix**: Call `simulator.update()` after color changes

**Issue**: Hardware lag
- **Cause**: Too many effects running simultaneously
- **Fix**: Use priority system to cancel lower-priority effects

**Issue**: Colors incorrect on hardware
- **Cause**: OpenRGB color calibration or device gamma
- **Fix**: Adjust in OpenRGB settings, not in effect definitions

---

## Version History

### Version 2.0 (Current)
- Visual Effects system introduced
- Base Effects (6 types)
- Keyboard Matrix Simulator
- Event Mapper v2 with multi-type support
- Color Schemes support

### Version 1.0 (Legacy)
- Fused Effects system
- Keyframe-based effects
- Basic spatial effects
- Event Mapper v1

---

## Contributing

When contributing new features:

1. **Follow existing patterns**: Use dataclasses, type hints, docstrings
2. **Test thoroughly**: Unit tests + integration tests + manual testing
3. **Update documentation**: This guide + user guide + code comments
4. **Maintain backward compatibility**: Don't break existing effects
5. **Consider performance**: Profile code, avoid blocking operations

---

## Further Reading

- **OpenRGB Documentation**: https://gitlab.com/CalcProgrammer1/OpenRGB
- **PyQt6 Documentation**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **Elite Dangerous Journal Documentation**: https://elite-journal.readthedocs.io/

---

*Last Updated: 2025-12-18*
*ED:Event2Led Version: 2.0*
