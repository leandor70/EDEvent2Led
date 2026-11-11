# Coordinate Normalization System - Design Document

**Created**: 2026-03-18
**Status**: Design Phase
**Phase**: 1.1 - Foundation

---

## 🎯 Goal

Transform LED positions from device-specific coordinates to **universal 0-1 normalized space**, enabling:
- Device-independent effect algorithms
- Multi-device effects (keyboard + mouse + strip simultaneously)
- Universal effect parameters (`center_x=0.5` always = "center")

---

## 📐 Current Coordinate Systems

### 1. KeyboardMatrix2D (MATRIX devices)
**Coordinates**: `(row, col)` - Discrete matrix positions
- Example: ASUS TUF K7 = 6 rows × 21 cols
- LED at row=3, col=10 → absolute matrix position
- **No spatial awareness** of physical dimensions

### 2. Linear1D (LINEAR devices)
**Coordinates**: `(world_x, world_y)` - Continuous world space
- Already has topology awareness via `device_topologies.json`
- Multi-segment LED strips with spatial layout
- Example: 5 segments at Y=5,9,13,17,21
- **Spatial awareness** via `get_led_world_position(zone_idx, local_idx)`

### 3. No Global Coordinate System
**Problem**: Each device operates in its own coordinate space
- Keyboard: row/col matrix
- LED strip: world_x/world_y from topology
- Mouse: linear index only
- **No unified space** for multi-device effects

---

## 🏗️ Proposed Architecture

### Global Bounding Box

```python
@dataclass
class GlobalBoundingBox:
    """
    Bounding box that encloses ALL active devices in a unified world space.
    """
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def width(self) -> float:
        return self.max_x - self.min_x

    def height(self) -> float:
        return self.max_y - self.min_y

    def normalize_point(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Normalize a world coordinate to [0,1] space.

        Returns:
            (norm_x, norm_y) where 0.0 <= norm_x, norm_y <= 1.0
        """
        norm_x = (world_x - self.min_x) / self.width() if self.width() > 0 else 0.5
        norm_y = (world_y - self.min_y) / self.height() if self.height() > 0 else 0.5
        return (norm_x, norm_y)
```

### Device World Coordinate Mapping

**Strategy**: Map each device type to a unified world coordinate system

#### MATRIX Devices (Keyboards)
```python
# KeyboardMatrix2D.get_led_world_position(led_index) -> (world_x, world_y)

# Approach 1: Treat row/col as world coordinates directly
world_x = col  # Column maps to X axis
world_y = row  # Row maps to Y axis

# Approach 2: Scale by unit cell size (for physical accuracy)
CELL_WIDTH = 1.0   # Each key = 1 unit wide
CELL_HEIGHT = 1.0  # Each key = 1 unit tall
world_x = col * CELL_WIDTH
world_y = row * CELL_HEIGHT
```

**Decision**: Use **Approach 1** (direct mapping) for simplicity.
- Keyboard at origin (0, 0) to (max_col, max_row)
- Consistent with Linear1D topology system

#### LINEAR Devices (LED Strips, RAM, Mouse)
```python
# Linear1D already has get_led_world_position()
world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)
# Returns coordinates from device_topologies.json
```

**No changes needed** - already has world coordinates!

#### SINGLE Devices (Single LED)
```python
# Single LED at arbitrary position
world_x, world_y = 0.0, 0.0  # Place at origin
```

---

## 🔧 Implementation Plan

### Phase A: VisualEffectRenderer Extensions

```python
# src/core/visual_effect_renderer.py

class VisualEffectRenderer:
    def __init__(self):
        # ... existing code ...

        # NEW: Track device world coordinates for normalization
        self._device_world_positions: Dict[str, List[Tuple[float, float]]] = {}
        self._global_bbox: Optional[GlobalBoundingBox] = None

    def _calculate_global_bbox(self) -> GlobalBoundingBox:
        """
        Calculate bounding box that encloses all active devices.

        Returns:
            GlobalBoundingBox spanning all device LED positions
        """
        if not self.active_effects:
            # No active devices - return unit square
            return GlobalBoundingBox(0.0, 0.0, 1.0, 1.0)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for device_id, active in self.active_effects.items():
            # Get all LED world positions for this device
            positions = self._get_device_world_positions(device_id, active.device_controller)

            for world_x, world_y in positions:
                min_x = min(min_x, world_x)
                min_y = min(min_y, world_y)
                max_x = max(max_x, world_x)
                max_y = max(max_y, world_y)

        # Add padding (10% on each side)
        padding_x = (max_x - min_x) * 0.1
        padding_y = (max_y - min_y) * 0.1

        return GlobalBoundingBox(
            min_x - padding_x,
            min_y - padding_y,
            max_x + padding_x,
            max_y + padding_y
        )

    def _get_device_world_positions(self, device_id: str, device_controller) -> List[Tuple[float, float]]:
        """
        Get world coordinates for all LEDs of a device.

        Returns:
            List of (world_x, world_y) tuples for each LED
        """
        # Check cache first
        if device_id in self._device_world_positions:
            return self._device_world_positions[device_id]

        positions = []
        controller = device_controller.controller

        # MATRIX device (KeyboardMatrix2D)
        if hasattr(controller, 'matrix_map'):
            matrix = controller
            for row in range(matrix.rows):
                for col in range(matrix.cols):
                    led_idx = matrix.get_led_index(row, col)
                    if led_idx is not None:
                        # Direct mapping: col→X, row→Y
                        world_x, world_y = float(col), float(row)
                        positions.append((world_x, world_y))

        # LINEAR device (Linear1D)
        elif hasattr(controller, 'led_count') and hasattr(controller, 'get_led_world_position'):
            linear = controller
            for led_idx in range(linear.led_count):
                try:
                    zone_idx, local_idx = linear.get_zone_and_local_index(led_idx)
                    world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)
                    positions.append((world_x, world_y))
                except:
                    # Fallback: sequential positioning
                    positions.append((float(led_idx), 0.0))

        # SINGLE or unknown - place at origin
        else:
            led_count = len(controller.device.leds) if hasattr(controller, 'device') else 1
            for i in range(led_count):
                positions.append((0.0, 0.0))

        # Cache for future calls
        self._device_world_positions[device_id] = positions
        return positions

    def _get_normalized_coords(self, device_id: str, led_index: int) -> Tuple[float, float]:
        """
        Get normalized [0,1] coordinates for a specific LED.

        Args:
            device_id: Device identifier
            led_index: LED index within device

        Returns:
            (norm_x, norm_y) in [0,1] space
        """
        # Ensure global bbox is computed
        if self._global_bbox is None:
            self._global_bbox = self._calculate_global_bbox()

        # Get LED world position
        positions = self._get_device_world_positions(device_id, self.active_effects[device_id].device_controller)

        if led_index >= len(positions):
            return (0.5, 0.5)  # Fallback to center

        world_x, world_y = positions[led_index]

        # Normalize to [0,1]
        return self._global_bbox.normalize_point(world_x, world_y)

    def get_all_normalized_positions(self, device_id: str) -> List[Tuple[float, float, int]]:
        """
        Get normalized coordinates for ALL LEDs of a device.

        Returns:
            List of (norm_x, norm_y, led_index) tuples
        """
        if self._global_bbox is None:
            self._global_bbox = self._calculate_global_bbox()

        positions = self._get_device_world_positions(device_id, self.active_effects[device_id].device_controller)

        normalized = []
        for led_idx, (world_x, world_y) in enumerate(positions):
            norm_x, norm_y = self._global_bbox.normalize_point(world_x, world_y)
            normalized.append((norm_x, norm_y, led_idx))

        return normalized
```

### Phase B: Device Controller Extensions

```python
# src/effects/keyboard_matrix_2d.py

class KeyboardMatrix2D:
    def get_led_world_position(self, led_index: int) -> Tuple[float, float]:
        """
        Get world coordinates for a specific LED.

        Args:
            led_index: LED index

        Returns:
            (world_x, world_y) - col/row as floats
        """
        coords = self.get_led_coords(led_index)
        if coords is None:
            return (0.0, 0.0)

        row, col = coords
        return (float(col), float(row))  # col→X, row→Y
```

```python
# src/effects/linear_1d.py

# Already has get_led_world_position() - NO CHANGES NEEDED!
```

### Phase C: Effect Algorithm Updates

**Option 1: Dual Coordinate Support** (Backward Compatible)
```python
# Effects accept BOTH world and normalized coordinates
class WaveEffect1D(Animated1DEffect):
    def __init__(self, linear, duration_ms, colors, direction='right', use_normalized=False):
        self.use_normalized = use_normalized
        # ... rest of init

    def _run_animation(self):
        for led_idx in range(self.led_count):
            if self.use_normalized:
                # NEW: Use normalized coordinates
                norm_x, norm_y = self.linear.get_normalized_position(led_idx)
                position = norm_x if direction in ['left', 'right'] else norm_y
            else:
                # OLD: Use world coordinates (existing behavior)
                world_x, world_y = self.linear.get_led_world_position(zone, local_idx)
                position = calculate_directional_position(world_x, world_y, direction)
```

**Option 2: Normalized Only** (Breaking Change)
```python
# Effects ONLY use normalized coordinates
class WaveEffect1D(Animated1DEffect):
    def _run_animation(self):
        for led_idx in range(self.led_count):
            # ALWAYS use normalized [0,1] space
            norm_x, norm_y = self.linear.get_normalized_position(led_idx)
            position = norm_x if direction in ['left', 'right'] else norm_y
```

**Decision**: Use **Option 1** (dual support) for gradual migration.

---

## 📊 Migration Strategy

### Stage 1: Infrastructure (Week 1)
- ✅ Design document
- [ ] Implement GlobalBoundingBox class
- [ ] Add _calculate_global_bbox() to VisualEffectRenderer
- [ ] Add _get_normalized_coords() to VisualEffectRenderer
- [ ] Add get_led_world_position() to KeyboardMatrix2D

### Stage 2: Effect Migration (Week 2)
- [ ] Add `use_normalized` parameter to all effect classes
- [ ] Update 5 core effects: Wave, Gradient, Explosion, Bloom, Pulse
- [ ] Test each effect with normalized=True vs False (should be identical visually)

### Stage 3: Multi-Device Testing (Week 3)
- [ ] Test keyboard-only effects with normalization
- [ ] Test LED strip-only effects with normalization
- [ ] Test keyboard + LED strip simultaneous effects
- [ ] Verify global bbox calculation is correct

### Stage 4: Full Migration (Week 4)
- [ ] Migrate remaining 12 effects to normalized coordinates
- [ ] Remove `use_normalized` flag (always use normalized)
- [ ] Update documentation and roadmap
- [ ] Phase 1.1 complete ✅

---

## 🎯 Success Criteria

- [ ] All 17 effect types work identically with normalized coordinates
- [ ] Global bbox correctly spans all active devices
- [ ] Multi-device effect (keyboard + mouse) renders correctly
- [ ] Parametric center point (center_x=0.5) works universally
- [ ] Zero visual regressions from coordinate migration

---

## 🔍 Edge Cases

### 1. Single Device Active
- Global bbox = device bbox only
- Normalized coords span full [0,1] range

### 2. Devices with Overlapping Positions
- Global bbox spans union of all positions
- Overlapping LEDs have same normalized coords (intended)

### 3. Horizontal vs Vertical Devices
- RAM (horizontal): Y=0, X=[0, N]
- LED strip (vertical): X=0, Y=[0, N]
- Global bbox adapts to encompass both

### 4. Empty Active Effects
- Return unit square GlobalBoundingBox(0, 0, 1, 1)
- Avoid division by zero

---

## 📝 API Examples

### Single Device Effect
```python
# User creates Wave effect on keyboard
renderer.start_effect(
    device_id="keyboard_01",
    device_controller=keyboard_controller,
    visual_effect=wave_effect
)

# Internally:
# 1. Renderer calculates global_bbox = keyboard bbox only
# 2. All keyboard LEDs normalized to [0,1] × [0,1]
# 3. Wave propagates across normalized X axis
```

### Multi-Device Effect
```python
# User creates Explosion effect on keyboard + mouse simultaneously
renderer.start_effect("keyboard_01", kb_controller, explosion_effect)
renderer.start_effect("mouse_01", mouse_controller, explosion_effect)

# Internally:
# 1. Renderer calculates global_bbox = union of keyboard + mouse
# 2. Explosion center at (0.5, 0.5) in normalized space
# 3. Both devices see wavefront expanding from SAME geometric center
# 4. Synchronized multi-device animation
```

---

**Status**: ✅ Design Complete - Ready for Implementation
