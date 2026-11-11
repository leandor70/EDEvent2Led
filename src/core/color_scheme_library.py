"""
Color Scheme Library - Management and persistence of Color Schemes.

This module handles loading, saving, and managing Color Schemes for LED-by-LED
keyboard lighting. Useful for Elite Dangerous key bindings where different
keys have different colors (e.g., red for weapons, blue for shields).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .base_effects import ColorScheme


class ColorSchemeLibrary:
    """
    Manages the library of Color Schemes.

    Handles:
    - Loading/saving from JSON
    - Adding/removing/updating schemes
    - Applying schemes to devices
    """

    def __init__(self, schemes_file: str = "config/color_schemes.json"):
        """
        Initialize the Color Scheme Library.

        Args:
            schemes_file: Path to JSON file storing color schemes
        """
        self.schemes_file = Path(schemes_file)
        self.schemes: Dict[str, ColorScheme] = {}
        self._ensure_file_exists()
        self.load_all()

    def _ensure_file_exists(self):
        """Ensure the schemes file and directory exist."""
        self.schemes_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.schemes_file.exists():
            # Create empty library with predefined schemes
            self._create_default_library()

    def _create_default_library(self):
        """Create a default library with predefined Color Schemes."""
        default_schemes = self._get_predefined_schemes()
        self.schemes = {scheme.id: scheme for scheme in default_schemes}
        self.save_all()

    def _get_predefined_schemes(self) -> List[ColorScheme]:
        """Get list of predefined Color Schemes to include in default library."""
        schemes = []

        # Elite Dangerous Combat Keys
        ed_combat = ColorScheme(
            id="ed_combat",
            name="Elite Dangerous - Combat",
            description="Combat-focused key coloring: Red for weapons, Blue for targets, Green for pips",
            device_type="keyboard",
            led_colors={
                # Example mappings - these would need to be customized per keyboard layout
                # Weapons (assuming keys 1-4 for weapon groups)
                0: (255, 0, 0),    # Key 1 - Primary fire
                1: (255, 50, 0),   # Key 2 - Secondary fire
                2: (200, 0, 0),    # Key 3 - Weapon group 3
                3: (200, 0, 0),    # Key 4 - Weapon group 4

                # Targeting (assuming Tab, T, Y keys)
                15: (0, 0, 255),   # Tab - Target ahead
                16: (0, 50, 255),  # T - Cycle targets
                17: (0, 100, 255), # Y - Select highest threat

                # Power distribution (assuming Arrow keys)
                80: (0, 255, 0),   # Up arrow - Systems pip
                81: (0, 255, 0),   # Left arrow - Engines pip
                82: (0, 255, 0),   # Right arrow - Weapons pip
                83: (0, 255, 0),   # Down arrow - Reset pips
            },
            key_bindings={
                "PrimaryFire": 0,
                "SecondaryFire": 1,
                "SelectTarget": 15,
                "CycleNextTarget": 16,
                "SelectHighestThreat": 17,
                "IncreaseSystemsPower": 80,
                "IncreaseEnginesPower": 81,
                "IncreaseWeaponsPower": 82,
                "ResetPowerDistribution": 83
            },
            metadata={
                "author": "System",
                "category": "Elite Dangerous",
                "description_detailed": "Optimized for combat: weapons in red, targeting in blue, pips in green"
            }
        )
        schemes.append(ed_combat)

        # Elite Dangerous Exploration Keys
        ed_exploration = ColorScheme(
            id="ed_exploration",
            name="Elite Dangerous - Exploration",
            description="Exploration-focused key coloring: Cyan for scanners, Yellow for lights",
            device_type="keyboard",
            led_colors={
                # Discovery scanner
                10: (0, 255, 255),   # FSS key
                11: (0, 200, 255),   # DSS key

                # Lights and night vision
                20: (255, 255, 0),   # Ship lights
                21: (255, 200, 0),   # Night vision

                # Flight assist
                30: (128, 0, 255),   # Flight assist toggle

                # Supercruise
                40: (0, 255, 128),   # Jump key
            },
            key_bindings={
                "FSSMode": 10,
                "DSSMode": 11,
                "ShipLights": 20,
                "NightVision": 21,
                "FlightAssist": 30,
                "HyperSuperCombination": 40
            },
            metadata={
                "author": "System",
                "category": "Elite Dangerous",
                "description_detailed": "Optimized for exploration: scanners in cyan, utilities in yellow"
            }
        )
        schemes.append(ed_exploration)

        # Elite Dangerous Trading/Mining Keys
        ed_trading = ColorScheme(
            id="ed_trading",
            name="Elite Dangerous - Trading/Mining",
            description="Trading and mining key coloring: Green for cargo, Orange for mining tools",
            device_type="keyboard",
            led_colors={
                # Cargo scoop
                50: (0, 255, 0),     # Cargo scoop toggle
                51: (0, 200, 0),     # Jettison cargo

                # Mining lasers and limpets
                60: (255, 128, 0),   # Mining laser
                61: (255, 100, 0),   # Prospector limpet
                62: (255, 80, 0),    # Collector limpet

                # Landing gear
                70: (128, 128, 255), # Landing gear
            },
            key_bindings={
                "ToggleCargoScoop": 50,
                "JettisonAllCargo": 51,
                "PrimaryFire": 60,  # Mining laser
                "ProspectorLimpet": 61,
                "CollectorLimpet": 62,
                "LandingGear": 70
            },
            metadata={
                "author": "System",
                "category": "Elite Dangerous",
                "description_detailed": "Optimized for trading and mining: cargo in green, mining tools in orange"
            }
        )
        schemes.append(ed_trading)

        return schemes

    def load_all(self):
        """Load all Color Schemes from JSON file."""
        try:
            with open(self.schemes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.schemes.clear()
            for scheme_data in data.get("schemes", []):
                scheme = ColorScheme.from_dict(scheme_data)
                self.schemes[scheme.id] = scheme

            print(f"Loaded {len(self.schemes)} Color Schemes from {self.schemes_file}")

        except FileNotFoundError:
            print(f"Color Schemes file not found: {self.schemes_file}, creating default library")
            self._create_default_library()
        except json.JSONDecodeError as e:
            print(f"Error parsing Color Schemes JSON: {e}")
            self.schemes = {}
        except Exception as e:
            print(f"Error loading Color Schemes: {e}")
            self.schemes = {}

    def save_all(self):
        """Save all Color Schemes to JSON file."""
        try:
            data = {
                "version": 1,
                "schemes": [scheme.to_dict() for scheme in self.schemes.values()]
            }

            with open(self.schemes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Saved {len(self.schemes)} Color Schemes to {self.schemes_file}")

        except Exception as e:
            print(f"Error saving Color Schemes: {e}")
            raise

    def add_scheme(self, scheme: ColorScheme) -> bool:
        """
        Add a new Color Scheme to the library.

        Args:
            scheme: ColorScheme to add

        Returns:
            True if added successfully, False if ID already exists
        """
        if scheme.id in self.schemes:
            print(f"Color Scheme with ID '{scheme.id}' already exists")
            return False

        self.schemes[scheme.id] = scheme
        return True

    def update_scheme(self, scheme: ColorScheme) -> bool:
        """
        Update an existing Color Scheme in the library.

        Args:
            scheme: ColorScheme to update

        Returns:
            True if updated successfully, False if ID not found
        """
        if scheme.id not in self.schemes:
            print(f"Color Scheme with ID '{scheme.id}' not found")
            return False

        self.schemes[scheme.id] = scheme
        return True

    def remove_scheme(self, scheme_id: str) -> bool:
        """
        Remove a Color Scheme from the library.

        Args:
            scheme_id: ID of scheme to remove

        Returns:
            True if removed successfully, False if not found
        """
        if scheme_id not in self.schemes:
            print(f"Color Scheme with ID '{scheme_id}' not found")
            return False

        # Check if it's a predefined scheme (don't allow removal)
        scheme = self.schemes[scheme_id]
        if scheme.metadata.get("author") == "System":
            print(f"Cannot remove predefined Color Scheme '{scheme_id}'")
            return False

        del self.schemes[scheme_id]
        return True

    def get_scheme(self, scheme_id: str) -> Optional[ColorScheme]:
        """
        Get a Color Scheme by ID.

        Args:
            scheme_id: ID of scheme to retrieve

        Returns:
            ColorScheme if found, None otherwise
        """
        return self.schemes.get(scheme_id)

    def get_all_schemes(self) -> List[ColorScheme]:
        """Get all Color Schemes in the library."""
        return list(self.schemes.values())

    def get_schemes_by_category(self, category: str) -> List[ColorScheme]:
        """
        Get all Color Schemes in a specific category.

        Args:
            category: Category to filter by (from metadata)

        Returns:
            List of ColorSchemes in that category
        """
        return [
            scheme for scheme in self.schemes.values()
            if scheme.metadata.get("category") == category
        ]

    def clone_scheme(self, scheme_id: str, new_id: str, new_name: str) -> Optional[ColorScheme]:
        """
        Clone an existing Color Scheme with a new ID and name.

        Args:
            scheme_id: ID of scheme to clone
            new_id: ID for the cloned scheme
            new_name: Name for the cloned scheme

        Returns:
            Cloned ColorScheme if successful, None otherwise
        """
        if scheme_id not in self.schemes:
            print(f"Color Scheme with ID '{scheme_id}' not found")
            return None

        if new_id in self.schemes:
            print(f"Color Scheme with ID '{new_id}' already exists")
            return None

        original = self.schemes[scheme_id]

        # Create a deep copy by serializing and deserializing
        cloned_data = original.to_dict()
        cloned_data["id"] = new_id
        cloned_data["name"] = new_name
        cloned_data["metadata"]["author"] = "User"  # Clones are user-created

        cloned = ColorScheme.from_dict(cloned_data)
        self.schemes[new_id] = cloned

        return cloned

    def export_scheme(self, scheme_id: str, export_path: str) -> bool:
        """
        Export a Color Scheme to a standalone JSON file.

        Args:
            scheme_id: ID of scheme to export
            export_path: Path where to save the exported file

        Returns:
            True if exported successfully, False otherwise
        """
        if scheme_id not in self.schemes:
            print(f"Color Scheme with ID '{scheme_id}' not found")
            return False

        try:
            scheme = self.schemes[scheme_id]
            data = {
                "version": 1,
                "scheme": scheme.to_dict()
            }

            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Exported Color Scheme '{scheme_id}' to {export_path}")
            return True

        except Exception as e:
            print(f"Error exporting Color Scheme: {e}")
            return False

    def import_scheme(self, import_path: str) -> Optional[ColorScheme]:
        """
        Import a Color Scheme from a standalone JSON file.

        Args:
            import_path: Path to the JSON file to import

        Returns:
            Imported ColorScheme if successful, None otherwise
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            scheme_data = data.get("scheme")
            if not scheme_data:
                print("Invalid import file: missing 'scheme' key")
                return None

            scheme = ColorScheme.from_dict(scheme_data)

            # Check if ID already exists
            if scheme.id in self.schemes:
                # Generate new unique ID
                base_id = scheme.id
                counter = 1
                while f"{base_id}_{counter}" in self.schemes:
                    counter += 1
                scheme.id = f"{base_id}_{counter}"
                scheme.name = f"{scheme.name} (Imported)"

            self.schemes[scheme.id] = scheme
            print(f"Imported Color Scheme '{scheme.id}' from {import_path}")

            return scheme

        except Exception as e:
            print(f"Error importing Color Scheme: {e}")
            return None

    def apply_scheme_to_device(self, scheme_id: str, device_controller) -> bool:
        """
        Apply a Color Scheme to a device.

        Args:
            scheme_id: ID of scheme to apply
            device_controller: Device controller (from unified_manager)

        Returns:
            True if applied successfully, False otherwise
        """
        scheme = self.get_scheme(scheme_id)
        if not scheme:
            print(f"Color Scheme '{scheme_id}' not found")
            return False

        try:
            # Apply each LED color from the scheme
            for led_index, color in scheme.led_colors.items():
                device_controller.controller.set_led(led_index, color)

            # Show the colors on the device
            device_controller.topology.device.show()

            print(f"Applied Color Scheme '{scheme_id}' to device")
            return True

        except Exception as e:
            print(f"Error applying Color Scheme: {e}")
            return False
