# Status.json Monitor Integration Guide

## Overview

This guide explains how to integrate the **StatusMonitor** module into EDLogReader to enable real-time RGB effects based on Elite Dangerous game state flags (overheating, interdiction, low fuel, etc.).

## Architecture

The StatusMonitor system works alongside the existing JournalReader:

```
Elite Dangerous Game
    |
    +-- Journal.log (discrete events: FSDJump, Docked, etc.)
    |       |
    |       v
    |   JournalReader --> EventProcessor --> UnifiedEffectManager --> RGB Hardware
    |
    +-- Status.json (continuous flags: Overheating, BeingInterdicted, etc.)
            |
            v
        StatusMonitor --> EventProcessor --> UnifiedEffectManager --> RGB Hardware
```

### Key Differences

| Aspect | Journal Events | Status Flags |
|--------|---------------|--------------|
| **Type** | Discrete one-time events | Continuous state flags |
| **Duration** | Fixed (effect plays once) | Persistent (loop while active) |
| **Example** | FSDJump (3 seconds) | Overheating (loops until temp drops) |
| **Effect Behavior** | `post_behavior: "turn_off"` | `post_behavior: "loop_effect"` |

## Implementation Steps

### Step 1: Modify main.py

Add StatusMonitor initialization after UnifiedEffectManager:

```python
# In main.py, after line 82:

# Initialize Event Processor
from journal.event_processor import EventProcessor
event_processor = EventProcessor(effect_manager)
event_processor.load_mappings("config/event_mappings.json")

# Initialize Status Monitor
from journal.status_monitor import StatusMonitor
from pathlib import Path

# Get journal directory from settings
journal_dir = settings.get_journal_directory()
if not journal_dir:
    # Default to Elite Dangerous journal directory
    journal_dir = Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous"

status_file = Path(journal_dir) / "Status.json"

# Create StatusMonitor with callback to event_processor
status_monitor = StatusMonitor(
    status_file_path=str(status_file),
    callback=event_processor.process_status_flag
)

# Start monitoring
if status_monitor.start():
    print(f"[OK] Status monitor started")
else:
    print(f"[WARNING] Could not start Status monitor")

# Store references for cleanup
window.status_monitor = status_monitor
window.event_processor = event_processor
```

### Step 2: Update Cleanup

Add StatusMonitor cleanup in main.py shutdown:

```python
# In main.py, before line 160 (cleanup section):

# Cleanup
print("Shutting down...")
if hasattr(window, 'status_monitor'):
    window.status_monitor.stop()
if hasattr(window, 'event_processor'):
    window.event_processor.stop_all_effects()
if effect_manager:
    effect_manager.clear_all()
```

### Step 3: Create Effect Mappings (Optional)

The effects are already created in `config/visual_effects.json` (17 new status effects added).

You can customize which Status flags trigger which effects by modifying `src/journal/status_monitor.py`:

```python
MONITORED_FLAGS = {
    20: {"name": "Overheating", "effect": "overheat_warning", "priority": 10},
    22: {"name": "BeingInterdicted", "effect": "interdiction_alert", "priority": 10},
    # ... etc
}
```

## Status Flag Reference

### Ship Flags (Flags field)

| Bit | Flag Name | Effect | Priority | Description |
|-----|-----------|--------|----------|-------------|
| 20 | Overheating | overheat_warning | 10 | Ship temperature critical |
| 22 | BeingInterdicted | interdiction_alert | 10 | Under interdiction |
| 23 | InDanger | danger_alert | 9 | General danger state |
| 19 | LowFuel | low_fuel_warning | 8 | Fuel reserves low |
| 16 | MassLocked | mass_locked | 7 | Cannot jump (mass lock) |
| 6 | HardpointsDeployed | combat_ready | 6 | Weapons deployed |
| 10 | SilentRunning | stealth_mode | 5 | Silent running active |
| 11 | ScoopingFuel | fuel_scooping | 5 | Fuel scoop active |
| 0 | Docked | docked_safe | 4 | Docked at station |
| 4 | Supercruise | supercruise_active | 3 | In supercruise |
| 30 | FSDJump | hyperspace_jump | 10 | FSD jump active |
| 3 | ShieldsUp | shields_active | 2 | Shields active |
| 28 | NightVision | night_vision_mode | 2 | Night vision on |

### On-Foot Flags (Flags2 field - Odyssey only)

| Bit | Flag Name | Effect | Priority | Description |
|-----|-----------|--------|----------|-------------|
| 6 | LowOxygen | low_oxygen_warning | 9 | Oxygen reserves low |
| 7 | LowHealth | low_health_warning | 9 | Health critical |
| 10 | VeryCold | extreme_cold | 8 | Extreme cold environment |
| 11 | VeryHot | extreme_heat | 8 | Extreme heat environment |
| 0 | OnFoot | on_foot_mode | 3 | On foot (disembarked) |
| 5 | AimDownSight | combat_aim | 5 | Aiming weapon |

## Effect Descriptions

### Critical Warnings (Priority 8-10)

- **overheat_warning**: Rapid red/orange pulsing (600ms loop)
- **interdiction_alert**: Fast purple/magenta flashing (400ms loop)
- **danger_alert**: Intense red breathing (700ms loop)
- **low_fuel_warning**: Yellow flashing (800ms loop)
- **low_oxygen_warning**: Cyan flashing (700ms loop)
- **low_health_warning**: Dark red pulsing (800ms loop)
- **extreme_cold**: Ice blue breathing (1000ms loop)
- **extreme_heat**: Red/orange pulsing (900ms loop)

### Combat Status (Priority 5-7)

- **combat_ready**: Subtle red glow (static)
- **mass_locked**: Dark blue static
- **combat_aim**: Red static (Odyssey)

### Navigation Status (Priority 2-4)

- **supercruise_active**: Light blue glow (static)
- **shields_active**: Cyan glow (static)
- **night_vision_mode**: Green NV glow (static)
- **docked_safe**: Green breathing then dim green (static)

### Utility Status (Priority 3-5)

- **stealth_mode**: Dark blue slow breathing (1500ms loop)
- **fuel_scooping**: Orange/yellow wave (1000ms loop)
- **on_foot_mode**: Subtle green glow (static)

## Testing

### Manual Testing

1. **Start OpenRGB** with SDK Server enabled
2. **Run EDLogReader**:
   ```bash
   python src/main.py
   ```
3. **Verify Status Monitor**:
   - Check console for: `[OK] Status monitor started`
   - Check for: `[StatusMonitor] Started monitoring <path>`

4. **Test with Elite Dangerous**:
   - Start Elite Dangerous
   - Trigger status flags (deploy hardpoints, enter supercruise, etc.)
   - Watch console for status changes:
     ```
     [StatusMonitor] Flags bit 6 ON: HardpointsDeployed -> Effect: combat_ready (Priority: 6)
     [EventProcessor] Status flag ON: HardpointsDeployed -> Effect: combat_ready (Priority: 6)
     ```
   - Verify RGB hardware shows correct effect

### Testing Without Elite Dangerous

Create a test Status.json file:

```python
# test_status.py
import json
import time
from pathlib import Path

test_dir = Path("test_journal")
test_dir.mkdir(exist_ok=True)
status_file = test_dir / "Status.json"

# Simulate flag changes
flags_sequence = [
    (0, "Normal"),
    (1 << 6, "Hardpoints deployed"),
    (1 << 20, "Overheating!"),
    (0, "Normal again")
]

for flags, description in flags_sequence:
    print(f"Setting flags: {flags} ({description})")
    with open(status_file, 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": "Status",
            "Flags": flags,
            "Flags2": 0
        }, f)
    time.sleep(3)  # Wait 3 seconds between changes
```

Run StatusMonitor pointing to `test_journal/Status.json`.

## Troubleshooting

### Status.json not found

**Symptom**: `[StatusMonitor] WARNING: Status.json not found`

**Solution**: Status.json is only created when Elite Dangerous is running. Start the game and the file will appear. StatusMonitor will continue monitoring and pick it up when created.

### Effects not triggering

**Symptom**: Console shows flag changes but no RGB effect

**Possible causes**:
1. Effect ID mismatch in `status_monitor.py`
   - Check that effect IDs match those in `config/visual_effects.json`

2. Effect not loaded in library
   - Verify effects exist: `python tools/list_effects.py`

3. Priority conflict
   - Higher priority journal event might be blocking status effect
   - Check console for: `[EventProcessor] Skipping ... (priority X < current Y)`

### Effects continue after flag deactivates

**Symptom**: RGB effect keeps looping after flag turns OFF

**Solution**: This indicates effect cancellation is not working. Check:
1. `process_status_flag()` is being called with `is_active=False`
2. `active_status_effects` dict is being cleared
3. `UnifiedEffectManager.stop_all_effects()` is implemented

Current limitation: Effect cancellation by ID not yet implemented in UnifiedEffectManager (TODO in code).

## Future Improvements

### Planned Features

1. **Effect Cancellation by ID**
   - Implement `cancel_effect(effect_id)` in UnifiedEffectManager
   - Allow precise stopping of individual status effects
   - Currently: effects finish naturally or get overridden

2. **Priority System Enhancement**
   - Allow multiple status effects with different priorities
   - Higher priority effects interrupt lower priority
   - Same priority effects blend or merge

3. **UI Integration**
   - Status flag indicator widget in UI
   - Real-time display of active flags
   - Toggle which flags to monitor
   - Adjust effect mappings from UI

4. **Effect Blending**
   - Blend multiple status effects (e.g., Overheating + InDanger)
   - Weighted color mixing based on priority
   - Spatial separation (left side vs right side)

## API Reference

### StatusMonitor Class

```python
class StatusMonitor:
    """Monitors Status.json for flag changes"""

    def __init__(self, status_file_path: str, callback: Callable):
        """
        Initialize monitor

        Args:
            status_file_path: Path to Status.json
            callback: Function(flag_name, is_active, effect_id, priority)
        """

    def start(self) -> bool:
        """Start monitoring. Returns True if successful."""

    def stop(self):
        """Stop monitoring and clear all effects."""

    def get_active_effects(self) -> Dict[str, str]:
        """Get currently active effects (flag_name -> effect_id)."""

    def get_flag_state(self, flag_name: str) -> bool:
        """Check if specific flag is active."""
```

### EventProcessor.process_status_flag()

```python
def process_status_flag(
    self,
    flag_name: str,
    is_active: bool,
    effect_id: str,
    priority: int
):
    """
    Process Status flag change

    Args:
        flag_name: Name of flag (e.g., "Overheating")
        is_active: True if flag ON, False if flag OFF
        effect_id: ID of effect to play
        priority: Effect priority (0-10)
    """
```

## Complete Integration Example

See `tools/test_status_integration.py` for a complete standalone example that demonstrates the full integration without requiring the main application.

## References

- [Status.json Documentation](https://elite-journal.readthedocs.io/en/latest/Status%20File.html)
- [Flags Field Reference](https://elite-journal.readthedocs.io/en/latest/Status%20File.html#flags)
- [Flags2 Field Reference (Odyssey)](https://elite-journal.readthedocs.io/en/latest/Status%20File.html#flags2)
