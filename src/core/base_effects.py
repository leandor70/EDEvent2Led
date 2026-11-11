"""
Base Effects System - Core Data Models

This module defines the foundational data structures for the Visual Effects system.
A Visual Effect is a sequence of Base Effect Steps, where each step is an atomic
lighting effect with specific parameters.

The 16 Base Effects are:
1.  Static Transition  - Fade to target color
2.  Breath             - Oscillate between two colors
3.  Color Cycle        - Animated color movement in a direction
4.  2 Color Nuance     - Spatial gradient between two colors
5.  4 Corner Nuance    - Bi-linear interpolation of 4 corner colors (2D only)
6.  Explosion          - Concentric circles expanding (2D only)
7.  Wave               - Directional color wave propagation (2D only)
8.  Bump               - Bidirectional wave with bounce-back (2D only)
9.  Glitch             - Random LED glitches with persistence and color variation
10. Fire               - Cellular automata fire simulation (2D only)
11. Matrix Rain        - Falling columns of light with trail (2D only)
12. Ocean Waves        - Superimposed sinusoids with 3-zone coloring (2D only)
13. Plasma             - Weighted sum of 2D sinusoids with HSV/palette mapping (2D only)
14. Aurora             - Vertical light bands with shimmer and additive blending (2D only)
15. Parallax Stars     - Lateral parallax scroll with depth layers (2D only)
16. Lightning          - Discrete lightning events with flash and bolt (2D only)
17. Keyboard Default   - Restore keyboard to a saved preset (soft transition)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import json
from pathlib import Path


class BaseEffectType(Enum):
    """Types of atomic base effects."""
    STATIC_TRANSITION = "static_transition"
    BREATH = "breath"
    COLOR_CYCLE = "color_cycle"
    TWO_COLOR_NUANCE = "two_color_nuance"
    FOUR_CORNER_NUANCE = "four_corner_nuance"
    BLOOM     = "bloom"          # expanding filled disk, fading from center (ex "explosion")
    EXPLOSION = "explosion_ring" # true expanding ring with decaying trail
    WAVE = "wave"
    BUMP = "bump"
    GLITCH = "glitch"
    # Natural physics effects (2D only)
    FIRE = "fire"
    MATRIX_RAIN = "matrix_rain"
    OCEAN_WAVES = "ocean_waves"
    PLASMA = "plasma"
    AURORA = "aurora"
    PARALLAX_STARS = "parallax_stars"
    LIGHTNING = "lightning"
    # Directional flash: 1/4 of the keyboard (the hit side) flashes and fades to black
    DIRECTIONAL_FLASH = "directional_flash"
    # Special built-in effect: restore keyboard to a saved preset
    KEYBOARD_DEFAULT = "keyboard_default"


class EffectDirection(Enum):
    """
    Effect direction values for directional effects.

    Supports 8 cardinal/diagonal directions + 2 radial modes.
    Used by: Wave, Gradient, Color Cycle, Bump, etc.
    """
    # Cardinal directions (4)
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"

    # Diagonal directions (4)
    DIAGONAL_TL_BR = "diagonal_tl_br"  # Top-Left to Bottom-Right
    DIAGONAL_TR_BL = "diagonal_tr_bl"  # Top-Right to Bottom-Left
    DIAGONAL_BL_TR = "diagonal_bl_tr"  # Bottom-Left to Top-Right
    DIAGONAL_BR_TL = "diagonal_br_tl"  # Bottom-Right to Top-Left

    # Radial modes (2)
    RADIAL_IN = "radial_in"    # From edges toward center
    RADIAL_OUT = "radial_out"  # From center toward edges

    # Legacy aliases for backward compatibility
    LEFT = "left"       # → LEFT_TO_RIGHT
    RIGHT = "right"     # → LEFT_TO_RIGHT
    UP = "up"           # → BOTTOM_TO_TOP
    DOWN = "down"       # → TOP_TO_BOTTOM
    TOP = "top"         # → TOP_TO_BOTTOM
    BOTTOM = "bottom"   # → BOTTOM_TO_TOP

    # Diagonal legacy aliases (used by UI 3×3 grid)
    TL = "tl"           # → DIAGONAL_BR_TL (toward Top-Left)
    TR = "tr"           # → DIAGONAL_BL_TR (toward Top-Right)
    BL = "bl"           # → DIAGONAL_TR_BL (toward Bottom-Left)
    BR = "br"           # → DIAGONAL_TL_BR (toward Bottom-Right)


@dataclass
class BaseEffectParams:
    """Parameters for a specific base effect."""
    colors: List[Tuple[int, int, int]]  # RGB colors (0-255)
    duration_ms: int  # Duration in milliseconds
    direction: Optional[str] = None  # EffectDirection value (left_to_right, top_to_bottom, diagonal_tl_br, radial_out, etc.)
    speed: Optional[float] = None  # For color_cycle (pixels per second or similar)
    num_loops: Optional[int] = None  # For explosion (0 or None = infinite)
    loop_infinite: bool = False  # For breath, color_cycle, explosion
    fade_in_ms: int = 0  # Fade-in duration in ms: 0=off, 150=fast, 400=medium, 800=slow
    # Glitch-specific parameters
    glitch_percentage: Optional[float] = None  # % of LEDs glitching simultaneously (0.0-1.0)
    glitch_duration_ms: Optional[int] = None  # Duration of single glitch flash
    duration_variability: Optional[float] = None  # Random variation in glitch duration (0.0-1.0)
    persistence_percentage: Optional[float] = None  # % of glitched LEDs that become persistent (0.0-1.0)
    color_variation: Optional[float] = None  # Random color variation amount (0.0-1.0)
    # Natural physics effects parameters (fire, matrix_rain, ocean_waves, plasma, aurora, parallax_stars, lightning)
    intensity: Optional[float] = None           # Fire: combustion intensity (0.0-1.0)
    density: Optional[float] = None             # MatrixRain/ParallaxStars: element density multiplier
    wave_weights: Optional[List[float]] = None  # Plasma: [h, v, circ, diag] weights
    height: Optional[float] = None             # Aurora: vertical position (0.0-1.0)
    tail_length: Optional[float] = None        # Aurora: curtain length (0.0-1.5)
    wave_frequency: Optional[float] = None     # Aurora: lateral undulation frequency
    ripple: Optional[float] = None             # Aurora: secondary wave intensity (0.0-1.0)
    bolt_interval_ms: Optional[int] = None     # Lightning: ms between strike events
    falloff:    Optional[float] = None          # Bloom (legacy): gradient shape exponent (0.5–3.0) - replaced by expansion_factor
    expansion_factor: Optional[float] = None    # Bloom: ring expansion multiplier (1.0-5.0, default 2.0)
    ring_width: Optional[float] = None          # Explosion: ring thickness as fraction of max_radius
    decay_rate: Optional[float] = None          # Explosion: trail decay speed (0.1–1.0)
    use_normalized: bool = False                # Use normalized [0,1] coordinates for spatial effects

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "colors": [list(c) for c in self.colors],
            "duration_ms": self.duration_ms,
            "direction": self.direction,
            "speed": self.speed,
            "num_loops": self.num_loops,
            "loop_infinite": self.loop_infinite,
            "fade_in_ms": self.fade_in_ms,
            "glitch_percentage": self.glitch_percentage,
            "glitch_duration_ms": self.glitch_duration_ms,
            "duration_variability": self.duration_variability,
            "persistence_percentage": self.persistence_percentage,
            "color_variation": self.color_variation,
            "intensity": self.intensity,
            "density": self.density,
            "wave_weights": self.wave_weights,
            "height": self.height,
            "tail_length": self.tail_length,
            "wave_frequency": self.wave_frequency,
            "ripple": self.ripple,
            "bolt_interval_ms": self.bolt_interval_ms,
            "falloff":    self.falloff,
            "expansion_factor": self.expansion_factor,
            "ring_width": self.ring_width,
            "decay_rate": self.decay_rate,
            "use_normalized": self.use_normalized,
        }

    @staticmethod
    def from_dict(data: dict) -> 'BaseEffectParams':
        """Create from dictionary loaded from JSON."""
        return BaseEffectParams(
            colors=[tuple(c) for c in data["colors"]],
            duration_ms=data["duration_ms"],
            direction=data.get("direction"),
            speed=data.get("speed"),
            num_loops=data.get("num_loops"),
            loop_infinite=data.get("loop_infinite", False),
            # Migration: old bool 'fade_in' → new int 'fade_in_ms' (true → 400ms Medium)
            fade_in_ms=data.get("fade_in_ms",
                                 400 if data.get("fade_in", False) else 0),
            glitch_percentage=data.get("glitch_percentage"),
            glitch_duration_ms=data.get("glitch_duration_ms"),
            duration_variability=data.get("duration_variability"),
            persistence_percentage=data.get("persistence_percentage"),
            color_variation=data.get("color_variation"),
            intensity=data.get("intensity"),
            density=data.get("density"),
            wave_weights=data.get("wave_weights"),
            height=data.get("height"),
            tail_length=data.get("tail_length"),
            wave_frequency=data.get("wave_frequency"),
            ripple=data.get("ripple"),
            bolt_interval_ms=data.get("bolt_interval_ms"),
            falloff=data.get("falloff"),
            expansion_factor=data.get("expansion_factor"),
            ring_width=data.get("ring_width"),
            decay_rate=data.get("decay_rate"),
            use_normalized=data.get("use_normalized", False),
        )


@dataclass
class BaseEffectStep:
    """A single step in a Visual Effect sequence."""
    step_id: int  # Order in sequence (0, 1, 2, ...)
    effect_type: BaseEffectType
    params: BaseEffectParams
    _ui_modified: bool = field(default=False, init=False, repr=False)  # UI-only flag, not serialized

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "step_id": self.step_id,
            "effect_type": self.effect_type.value,
            "params": self.params.to_dict()
        }

    @staticmethod
    def from_dict(data: dict) -> 'BaseEffectStep':
        """Create from dictionary loaded from JSON."""
        effect_type_str = data["effect_type"]
        # Migration: old "explosion" (filled-disk / bloom) → new "bloom" type.
        # The new "explosion_ring" is the true expanding-ring implementation.
        if effect_type_str == "explosion":
            effect_type_str = "bloom"
        return BaseEffectStep(
            step_id=data["step_id"],
            effect_type=BaseEffectType(effect_type_str),
            params=BaseEffectParams.from_dict(data["params"])
        )


class PostSequenceBehavior(Enum):
    """Behavior after Visual Effect sequence completes."""
    STATIC_COLOR = "static_color"  # Keep the final animation frame (default)
    LOOP_EFFECT = "loop_effect"  # Loop a specific step indefinitely
    COLOR_SCHEME = "color_scheme"  # Apply a color scheme


@dataclass
class VisualEffect:
    """
    Visual Effect = Ordered sequence of Base Effect Steps.

    This is the main entity that users create, edit, and assign to game events.
    """
    id: str  # Unique identifier
    name: str  # Display name
    description: str  # User description
    steps: List[BaseEffectStep]  # Ordered sequence of effects
    topology_support: List[str]  # ["2D"], ["1D"], ["0D"], or combinations
    post_behavior: PostSequenceBehavior  # What to do after sequence ends
    post_behavior_data: Optional[Dict[str, Any]] = None  # Additional data for post_behavior
    category: str = "custom"  # "predefined" or "custom"
    metadata: Dict[str, Any] = field(default_factory=dict)  # Author, tags, etc.
    is_quick_created: bool = False  # True if created via quick editor (needs refinement)
    created_timestamp: Optional[float] = None  # Unix timestamp of creation

    def total_duration_ms(self) -> int:
        """
        Calculate total duration of all non-infinite steps.
        If any step has loop_infinite=True, returns duration up to that step.
        """
        total = 0
        for step in self.steps:
            if step.params.loop_infinite:
                # Stop counting at first infinite loop
                break
            total += step.params.duration_ms
        return total

    def supports_topology(self, topology: str) -> bool:
        """Check if this effect supports a specific topology (2D, 1D, 0D)."""
        return topology in self.topology_support or "all" in [t.lower() for t in self.topology_support]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "topology_support": self.topology_support,
            "post_behavior": self.post_behavior.value,
            "post_behavior_data": self.post_behavior_data,
            "category": self.category,
            "metadata": self.metadata,
            "is_quick_created": self.is_quick_created,
            "created_timestamp": self.created_timestamp
        }

    @staticmethod
    def from_dict(data: dict) -> 'VisualEffect':
        """Create from dictionary loaded from JSON."""
        return VisualEffect(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            steps=[BaseEffectStep.from_dict(s) for s in data["steps"]],
            topology_support=data.get("topology_support", ["2D", "1D", "0D"]),
            post_behavior=PostSequenceBehavior(data.get("post_behavior", "static_color")),
            post_behavior_data=data.get("post_behavior_data"),
            category=data.get("category", "custom"),
            metadata=data.get("metadata", {}),
            is_quick_created=data.get("is_quick_created", False),
            created_timestamp=data.get("created_timestamp")
        )


@dataclass
class ColorScheme:
    """
    Color Scheme = LED-by-LED color mapping for keyboards.

    Useful for setting up Elite Dangerous key bindings with specific colors
    (e.g., red for weapons, blue for shields, green for pips).
    """
    id: str  # Unique identifier
    name: str  # Display name
    description: str  # User description
    device_type: str = "keyboard"  # For now, only keyboards supported
    led_colors: Dict[int, Tuple[int, int, int]] = field(default_factory=dict)  # led_index -> RGB
    key_bindings: Optional[Dict[str, int]] = None  # Elite Dangerous key name -> led_index
    metadata: Dict[str, Any] = field(default_factory=dict)  # Author, created date, etc.

    def set_led_color(self, led_index: int, color: Tuple[int, int, int]):
        """Set color for a specific LED."""
        self.led_colors[led_index] = color

    def get_led_color(self, led_index: int) -> Optional[Tuple[int, int, int]]:
        """Get color for a specific LED, or None if not set."""
        return self.led_colors.get(led_index)

    def clear_led(self, led_index: int):
        """Remove color mapping for a specific LED."""
        if led_index in self.led_colors:
            del self.led_colors[led_index]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "device_type": self.device_type,
            "led_colors": {str(k): list(v) for k, v in self.led_colors.items()},
            "key_bindings": self.key_bindings,
            "metadata": self.metadata
        }

    @staticmethod
    def from_dict(data: dict) -> 'ColorScheme':
        """Create from dictionary loaded from JSON."""
        return ColorScheme(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            device_type=data.get("device_type", "keyboard"),
            led_colors={int(k): tuple(v) for k, v in data.get("led_colors", {}).items()},
            key_bindings=data.get("key_bindings"),
            metadata=data.get("metadata", {})
        )


# Utility functions for working with base effects

def create_default_visual_effect(name: str, effect_id: str) -> VisualEffect:
    """Create a simple default Visual Effect with a single static transition."""
    return VisualEffect(
        id=effect_id,
        name=name,
        description="Default visual effect",
        steps=[
            BaseEffectStep(
                step_id=0,
                effect_type=BaseEffectType.STATIC_TRANSITION,
                params=BaseEffectParams(
                    colors=[(255, 255, 255)],
                    duration_ms=1000,
                    loop_infinite=False
                )
            )
        ],
        topology_support=["2D", "1D", "0D"],
        post_behavior=PostSequenceBehavior.STATIC_COLOR,
        category="custom"
    )


def create_default_color_scheme(name: str, scheme_id: str) -> ColorScheme:
    """Create an empty default Color Scheme."""
    return ColorScheme(
        id=scheme_id,
        name=name,
        description="Default color scheme",
        device_type="keyboard",
        led_colors={},
        metadata={"author": "User", "created": "auto"}
    )
