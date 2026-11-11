"""
Active Effect State - Dataclass for tracking playing effects.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, List


@dataclass
class ActiveVisualEffect:
    """Runtime state for a visual effect currently playing on a device."""

    device_controller: Any
    visual_effect: Any
    spatial_effects: List[Any]          # one slot per step (None = not yet created)
    current_step_index: int = 0
    step_start_time: float = field(default_factory=time.time)
    simulator_mode: bool = False
    on_complete: Optional[Callable] = None
    current_effect: Optional[Any] = None  # shortcut to spatial_effects[current_step_index]
