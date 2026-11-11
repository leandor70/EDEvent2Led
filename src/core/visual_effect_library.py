"""
Visual Effect Library - Management and persistence of Visual Effects.

This module handles loading, saving, and managing the library of Visual Effects.
Visual Effects are stored in config/visual_effects.json.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from .base_effects import VisualEffect, BaseEffectType, BaseEffectStep, BaseEffectParams, PostSequenceBehavior

# ID of the built-in Keyboard Default effect (protected from delete/edit)
KEYBOARD_DEFAULT_ID = "keyboard_default"


def _build_keyboard_default_effect() -> VisualEffect:
    """
    Build the built-in Keyboard Default effect.

    This effect is NOT stored in visual_effects.json — it is injected at
    runtime as the first item in get_all_effects(). Preset id and transition
    duration are read live from config/keyboard_presets.json.
    """
    # Read current preset and transition duration from keyboard_presets.json
    preset_id = '1'
    duration_ms = 800
    try:
        presets_path = Path('config/keyboard_presets.json')
        if presets_path.exists():
            data = json.loads(presets_path.read_text(encoding='utf-8'))
            preset_id = str(data.get('active_preset', '1'))
            duration_ms = int(data.get('transition_ms', 800))
    except Exception:
        pass

    step = BaseEffectStep(
        step_id="step_0",
        effect_type=BaseEffectType.KEYBOARD_DEFAULT,
        params=BaseEffectParams(
            colors=[],
            duration_ms=duration_ms,
            direction=preset_id,
        ),
    )
    return VisualEffect(
        id=KEYBOARD_DEFAULT_ID,
        name="Keyboard Default",
        description="Applies the configured keyboard preset colors with a soft transition",
        steps=[step],
        category="general",
        topology_support=["2D"],
        post_behavior=PostSequenceBehavior.STATIC_COLOR,
        metadata={
            "is_special": True,
            "not_editable": True,
            "not_deletable": True,
        },
    )


class VisualEffectLibrary:
    """
    Manages the library of Visual Effects.

    Handles:
    - Loading/saving from JSON
    - Adding/removing/updating effects
    - Querying effects by ID, category, topology
    """

    def __init__(self, effects_file: str = "config/visual_effects.json"):
        """
        Initialize the Visual Effect Library.

        Args:
            effects_file: Path to JSON file storing visual effects
        """
        self.effects_file = Path(effects_file)
        self.effects: Dict[str, VisualEffect] = {}
        self._ensure_file_exists()
        self.load_all()

    def _ensure_file_exists(self):
        """Ensure the effects file and directory exist."""
        self.effects_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.effects_file.exists():
            # Create empty library with predefined effects
            self._create_default_library()

    def _create_default_library(self):
        """Create a default library with predefined Visual Effects."""
        default_effects = self._get_predefined_effects()
        self.effects = {eff.id: eff for eff in default_effects}
        self.save_all()

    def _get_predefined_effects(self) -> List[VisualEffect]:
        """Get list of predefined Visual Effects to include in default library."""
        effects = []

        # Hyperspace Jump - Blue transition + Explosion
        hyperspace = VisualEffect(
            id="hyperspace_jump",
            name="Hyperspace Jump",
            description="Blue transition followed by white explosion, perfect for FSD jumps",
            steps=[
                BaseEffectStep(
                    step_id=0,
                    effect_type=BaseEffectType.STATIC_TRANSITION,
                    params=BaseEffectParams(
                        colors=[(0, 0, 255)],
                        duration_ms=500,
                        loop_infinite=False
                    )
                ),
                BaseEffectStep(
                    step_id=1,
                    effect_type=BaseEffectType.EXPLOSION,
                    params=BaseEffectParams(
                        colors=[(0, 50, 255), (0, 150, 255), (100, 200, 255), (200, 220, 255), (255, 255, 255)],
                        duration_ms=1200,
                        num_loops=1,
                        loop_infinite=False
                    )
                ),
                BaseEffectStep(
                    step_id=2,
                    effect_type=BaseEffectType.BREATH,
                    params=BaseEffectParams(
                        colors=[(255, 255, 255), (0, 0, 0)],
                        duration_ms=2000,
                        loop_infinite=False
                    )
                )
            ],
            topology_support=["2D", "1D"],
            post_behavior=PostSequenceBehavior.STATIC_COLOR,
            category="predefined",
            metadata={
                "author": "System",
                "tags": ["hyperspace", "jump", "travel"]
            }
        )
        effects.append(hyperspace)

        # Combat Alert - Red pulsing
        combat = VisualEffect(
            id="combat_alert",
            name="Combat Alert",
            description="Pulsing red alert for combat situations",
            steps=[
                BaseEffectStep(
                    step_id=0,
                    effect_type=BaseEffectType.BREATH,
                    params=BaseEffectParams(
                        colors=[(255, 0, 0), (100, 0, 0)],
                        duration_ms=800,
                        loop_infinite=True
                    )
                )
            ],
            topology_support=["2D", "1D", "0D"],
            post_behavior=PostSequenceBehavior.STATIC_COLOR,
            category="predefined",
            metadata={
                "author": "System",
                "tags": ["combat", "alert", "warning"]
            }
        )
        effects.append(combat)

        # Docked - Green wave
        docked = VisualEffect(
            id="docked_safe",
            name="Docked (Safe)",
            description="Calming green effect when docked at station",
            steps=[
                BaseEffectStep(
                    step_id=0,
                    effect_type=BaseEffectType.STATIC_TRANSITION,
                    params=BaseEffectParams(
                        colors=[(0, 255, 0)],
                        duration_ms=1000,
                        loop_infinite=False
                    )
                ),
                BaseEffectStep(
                    step_id=1,
                    effect_type=BaseEffectType.BREATH,
                    params=BaseEffectParams(
                        colors=[(0, 255, 0), (0, 100, 0)],
                        duration_ms=2000,
                        loop_infinite=False
                    )
                )
            ],
            topology_support=["2D", "1D", "0D"],
            post_behavior=PostSequenceBehavior.STATIC_COLOR,
            post_behavior_data={"color": [0, 50, 0]},
            category="predefined",
            metadata={
                "author": "System",
                "tags": ["docked", "station", "safe"]
            }
        )
        effects.append(docked)

        # Discovery - White sparkle
        discovery = VisualEffect(
            id="discovery_flash",
            name="Discovery Flash",
            description="Bright white flash for discoveries and scans",
            steps=[
                BaseEffectStep(
                    step_id=0,
                    effect_type=BaseEffectType.STATIC_TRANSITION,
                    params=BaseEffectParams(
                        colors=[(255, 255, 255)],
                        duration_ms=300,
                        loop_infinite=False
                    )
                ),
                BaseEffectStep(
                    step_id=1,
                    effect_type=BaseEffectType.STATIC_TRANSITION,
                    params=BaseEffectParams(
                        colors=[(0, 0, 0)],
                        duration_ms=500,
                        loop_infinite=False
                    )
                )
            ],
            topology_support=["2D", "1D", "0D"],
            post_behavior=PostSequenceBehavior.STATIC_COLOR,
            category="predefined",
            metadata={
                "author": "System",
                "tags": ["discovery", "scan", "exploration"]
            }
        )
        effects.append(discovery)

        # Rainbow Cycle - For testing
        rainbow = VisualEffect(
            id="rainbow_cycle",
            name="Rainbow Cycle",
            description="Continuous rainbow cycling effect for testing",
            steps=[
                BaseEffectStep(
                    step_id=0,
                    effect_type=BaseEffectType.COLOR_CYCLE,
                    params=BaseEffectParams(
                        colors=[
                            (255, 0, 0), (255, 127, 0), (255, 255, 0),
                            (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
                        ],
                        duration_ms=5000,
                        direction="right",
                        speed=1.0,
                        loop_infinite=True
                    )
                )
            ],
            topology_support=["2D", "1D"],
            post_behavior=PostSequenceBehavior.STATIC_COLOR,
            category="predefined",
            metadata={
                "author": "System",
                "tags": ["test", "rainbow", "demo"]
            }
        )
        effects.append(rainbow)

        return effects

    def load_all(self):
        """Load all Visual Effects from JSON file."""
        try:
            with open(self.effects_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.effects.clear()
            for effect_data in data.get("effects", []):
                effect = VisualEffect.from_dict(effect_data)
                self.effects[effect.id] = effect

            print(f"Loaded {len(self.effects)} Visual Effects from {self.effects_file}")

        except FileNotFoundError:
            print(f"Visual Effects file not found: {self.effects_file}, creating default library")
            self._create_default_library()
        except json.JSONDecodeError as e:
            print(f"Error parsing Visual Effects JSON: {e}")
            self.effects = {}
        except Exception as e:
            print(f"Error loading Visual Effects: {e}")
            self.effects = {}

    def save_all(self):
        """Save all Visual Effects to JSON file."""
        try:
            data = {
                "version": 1,
                "effects": [effect.to_dict() for effect in self.effects.values()]
            }

            with open(self.effects_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Saved {len(self.effects)} Visual Effects to {self.effects_file}")

        except Exception as e:
            print(f"Error saving Visual Effects: {e}")
            raise

    def add_effect(self, effect: VisualEffect) -> bool:
        """
        Add a new Visual Effect to the library.

        Args:
            effect: VisualEffect to add

        Returns:
            True if added successfully, False if ID already exists
        """
        if effect.id in self.effects:
            print(f"Visual Effect with ID '{effect.id}' already exists")
            return False

        self.effects[effect.id] = effect
        return True

    def update_effect(self, effect: VisualEffect) -> bool:
        """
        Update an existing Visual Effect in the library.

        Args:
            effect: VisualEffect to update

        Returns:
            True if updated successfully, False if ID not found or is protected
        """
        if effect.id == KEYBOARD_DEFAULT_ID:
            # Persist the step's preset id (direction) and transition duration
            # to keyboard_presets.json so _build_keyboard_default_effect() picks them up.
            if effect.steps:
                step = effect.steps[0]
                preset_id = step.params.direction or '1'
                duration_ms = step.params.duration_ms or 800
                try:
                    presets_path = Path('config/keyboard_presets.json')
                    data = json.loads(presets_path.read_text(encoding='utf-8')) if presets_path.exists() else {}
                    data['active_preset'] = str(preset_id)
                    data['transition_ms'] = int(duration_ms)
                    presets_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                except Exception as e:
                    print(f"Warning: could not save keyboard_default config: {e}")
            return True

        if effect.id not in self.effects:
            print(f"Visual Effect with ID '{effect.id}' not found")
            return False

        self.effects[effect.id] = effect
        return True

    def remove_effect(self, effect_id: str) -> bool:
        """
        Remove a Visual Effect from the library.

        Args:
            effect_id: ID of effect to remove

        Returns:
            True if removed successfully, False if not found or is protected
        """
        if effect_id == KEYBOARD_DEFAULT_ID:
            print(f"Cannot remove built-in effect '{KEYBOARD_DEFAULT_ID}'")
            return False

        if effect_id not in self.effects:
            print(f"Visual Effect with ID '{effect_id}' not found")
            return False

        effect = self.effects[effect_id]
        if effect.metadata.get("not_deletable"):
            print(f"Cannot remove protected Visual Effect '{effect_id}'")
            return False

        del self.effects[effect_id]
        return True

    def get_effect(self, effect_id: str) -> Optional[VisualEffect]:
        """
        Get a Visual Effect by ID.

        Args:
            effect_id: ID of effect to retrieve

        Returns:
            VisualEffect if found, None otherwise
        """
        if effect_id == KEYBOARD_DEFAULT_ID:
            return _build_keyboard_default_effect()
        return self.effects.get(effect_id)

    def get_all_effects(self) -> List[VisualEffect]:
        """Get all Visual Effects in the library (keyboard_default always first)."""
        return [_build_keyboard_default_effect()] + list(self.effects.values())

    def get_effects_by_category(self, category: str) -> List[VisualEffect]:
        """
        Get all Visual Effects in a specific category.

        Args:
            category: Category to filter by ("predefined" or "custom")

        Returns:
            List of VisualEffects in that category
        """
        return [eff for eff in self.effects.values() if eff.category == category]

    def get_effects_by_topology(self, topology: str) -> List[VisualEffect]:
        """
        Get all Visual Effects that support a specific topology.

        Args:
            topology: Topology to filter by ("2D", "1D", "0D")

        Returns:
            List of VisualEffects supporting that topology
        """
        return [eff for eff in self.effects.values() if eff.supports_topology(topology)]

    def clone_effect(self, effect_id: str, new_id: str, new_name: str) -> Optional[VisualEffect]:
        """
        Clone an existing Visual Effect with a new ID and name.

        Args:
            effect_id: ID of effect to clone
            new_id: ID for the cloned effect
            new_name: Name for the cloned effect

        Returns:
            Cloned VisualEffect if successful, None otherwise
        """
        if effect_id not in self.effects:
            print(f"Visual Effect with ID '{effect_id}' not found")
            return None

        if new_id in self.effects:
            print(f"Visual Effect with ID '{new_id}' already exists")
            return None

        original = self.effects[effect_id]

        # Create a deep copy by serializing and deserializing
        cloned_data = original.to_dict()
        cloned_data["id"] = new_id
        cloned_data["name"] = new_name
        cloned_data["category"] = original.category  # Clone inherits category

        cloned = VisualEffect.from_dict(cloned_data)
        self.effects[new_id] = cloned

        return cloned

    def export_effect(self, effect_id: str, export_path: str) -> bool:
        """
        Export a Visual Effect to a standalone JSON file.

        Args:
            effect_id: ID of effect to export
            export_path: Path where to save the exported file

        Returns:
            True if exported successfully, False otherwise
        """
        if effect_id not in self.effects:
            print(f"Visual Effect with ID '{effect_id}' not found")
            return False

        try:
            effect = self.effects[effect_id]
            data = {
                "version": 1,
                "effect": effect.to_dict()
            }

            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Exported Visual Effect '{effect_id}' to {export_path}")
            return True

        except Exception as e:
            print(f"Error exporting Visual Effect: {e}")
            return False

    def import_effect(self, import_path: str) -> Optional[VisualEffect]:
        """
        Import a Visual Effect from a standalone JSON file.

        Args:
            import_path: Path to the JSON file to import

        Returns:
            Imported VisualEffect if successful, None otherwise
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            effect_data = data.get("effect")
            if not effect_data:
                print("Invalid import file: missing 'effect' key")
                return None

            effect = VisualEffect.from_dict(effect_data)

            # Check if ID already exists
            if effect.id in self.effects:
                # Generate new unique ID
                base_id = effect.id
                counter = 1
                while f"{base_id}_{counter}" in self.effects:
                    counter += 1
                effect.id = f"{base_id}_{counter}"
                effect.name = f"{effect.name} (Imported)"

            self.effects[effect.id] = effect
            print(f"Imported Visual Effect '{effect.id}' from {import_path}")

            return effect

        except Exception as e:
            print(f"Error importing Visual Effect: {e}")
            return None
