"""
Device topology detection and classification for LED devices.
Automatically detects whether devices have 1D (linear) or 2D (matrix) LED layouts.
"""
from typing import Optional, List, Tuple
from enum import Enum
from utils.openrgb_client import DeviceType


class TopologyType(Enum):
    """LED device topology types."""
    LINEAR = "1D"      # Single row/strip of LEDs (RAM, LED strips, mice)
    MATRIX = "2D"      # 2D grid of LEDs (keyboards, large LED panels)
    SINGLE = "0D"      # Single LED or all LEDs treated as one
    UNKNOWN = "unknown"


class DeviceTopology:
    """
    Represents the physical LED topology of a device.
    """

    def __init__(self, device, topology_type: TopologyType, led_count: int,
                 matrix_map: Optional[List[List[Optional[int]]]] = None,
                 dimensions: Optional[Tuple[int, int]] = None,
                 name: Optional[str] = None):
        """
        Initialize device topology.

        Args:
            device: OpenRGB device object (can be None for mock devices)
            topology_type: Type of topology (LINEAR, MATRIX, SINGLE)
            led_count: Total number of LEDs
            matrix_map: For MATRIX type, the 2D LED mapping
            dimensions: (rows, cols) for MATRIX or (length,) for LINEAR
            name: Optional name for mock devices (when device=None)
        """
        self.device = device
        self.topology_type = topology_type
        self.led_count = led_count
        self.matrix_map = matrix_map
        self.dimensions = dimensions

        # Device metadata
        if device is not None:
            self.name = device.name
            self.device_type = device.type
            self.zones = len(device.zones)
        else:
            # Mock device for testing/simulation
            self.name = name if name else "Mock Device"
            self.device_type = None
            self.zones = 0

    def __repr__(self):
        if self.topology_type == TopologyType.MATRIX:
            return f"<DeviceTopology: {self.name} [{self.topology_type.value} {self.dimensions[0]}×{self.dimensions[1]}] {self.led_count} LEDs>"
        elif self.topology_type == TopologyType.LINEAR:
            return f"<DeviceTopology: {self.name} [{self.topology_type.value}] {self.led_count} LEDs>"
        else:
            return f"<DeviceTopology: {self.name} [{self.topology_type.value}] {self.led_count} LEDs>"


class TopologyDetector:
    """
    Detects and analyzes LED topology for OpenRGB devices.
    """

    @staticmethod
    def detect(device) -> DeviceTopology:
        """
        Automatically detect device topology.

        Args:
            device: OpenRGB device object

        Returns:
            DeviceTopology object describing the device's LED layout
        """
        led_count = len(device.leds)

        # Check for 2D matrix topology
        matrix_info = TopologyDetector._detect_matrix(device)
        if matrix_info:
            matrix_map, rows, cols = matrix_info
            return DeviceTopology(
                device,
                TopologyType.MATRIX,
                led_count,
                matrix_map=matrix_map,
                dimensions=(rows, cols)
            )

        # Check for 1D linear topology
        if TopologyDetector._is_linear_device(device):
            return DeviceTopology(
                device,
                TopologyType.LINEAR,
                led_count,
                dimensions=(led_count,)
            )

        # Single LED or unknown
        if led_count <= 1:
            return DeviceTopology(
                device,
                TopologyType.SINGLE,
                led_count,
                dimensions=(1,)
            )

        # Default to linear for multi-LED devices without clear topology
        return DeviceTopology(
            device,
            TopologyType.LINEAR,
            led_count,
            dimensions=(led_count,)
        )

    @staticmethod
    def _detect_matrix(device) -> Optional[Tuple[List[List[Optional[int]]], int, int]]:
        """
        Try to detect 2D matrix layout.

        Returns:
            (matrix_map, rows, cols) tuple or None if not a matrix device
        """
        # Check if any zone has matrix_map attribute
        for zone in device.zones:
            if hasattr(zone, 'matrix_map') and zone.matrix_map:
                matrix_map = zone.matrix_map
                rows = len(matrix_map)
                cols = len(matrix_map[0]) if matrix_map else 0

                # Validate it's a real matrix (not just a single row)
                if rows > 1 and cols > 1:
                    return (matrix_map, rows, cols)

        return None

    @staticmethod
    def _is_linear_device(device) -> bool:
        """
        Determine if device is linear (1D).

        Returns:
            True if device is likely linear topology
        """
        # Device types that are typically linear
        linear_types = {
            DeviceType.DRAM,          # RAM modules
            DeviceType.LEDSTRIP,      # LED strips
            DeviceType.MOUSE,         # Mouse (usually linear strip)
            DeviceType.MOUSEMAT,      # Mouse mat (usually perimeter strip)
            DeviceType.HEADSET,       # Headset (linear around band)
            DeviceType.HEADSET_STAND, # Stand (typically linear)
            DeviceType.GPU,           # GPU (usually linear strip on edge)
            DeviceType.COOLER,        # Coolers (usually linear or ring)
        }

        if device.type in linear_types:
            return True

        # If single zone with many LEDs but no matrix, assume linear
        if len(device.zones) == 1 and len(device.leds) > 1:
            zone = device.zones[0]
            if not hasattr(zone, 'matrix_map') or not zone.matrix_map:
                return True

        return False

    @staticmethod
    def detect_all(client) -> List[DeviceTopology]:
        """
        Detect topology for all devices.

        Args:
            client: OpenRGBClient instance

        Returns:
            List of DeviceTopology objects for all devices
        """
        topologies = []
        for device in client.devices:
            topology = TopologyDetector.detect(device)
            topologies.append(topology)
        return topologies

    @staticmethod
    def group_by_topology(topologies: List[DeviceTopology]) -> dict:
        """
        Group devices by topology type.

        Args:
            topologies: List of DeviceTopology objects

        Returns:
            Dict mapping TopologyType -> List[DeviceTopology]
        """
        groups = {
            TopologyType.MATRIX: [],
            TopologyType.LINEAR: [],
            TopologyType.SINGLE: [],
            TopologyType.UNKNOWN: []
        }

        for topology in topologies:
            groups[topology.topology_type].append(topology)

        return groups

    @staticmethod
    def print_topology_report(topologies: List[DeviceTopology]):
        """
        Print a detailed topology report for all devices.

        Args:
            topologies: List of DeviceTopology objects
        """
        print("=" * 70)
        print("DEVICE TOPOLOGY REPORT")
        print("=" * 70)
        print()

        groups = TopologyDetector.group_by_topology(topologies)

        for topo_type, devices in groups.items():
            if not devices:
                continue

            print(f"{topo_type.value.upper()} DEVICES ({len(devices)}):")
            print("-" * 70)

            for topology in devices:
                device_type_name = TopologyDetector._get_device_type_name(topology.device_type)
                print(f"  {topology.name}")
                print(f"    Type: {device_type_name}")
                print(f"    LEDs: {topology.led_count}")

                if topology.topology_type == TopologyType.MATRIX:
                    rows, cols = topology.dimensions
                    print(f"    Matrix: {rows} rows x {cols} cols")
                elif topology.topology_type == TopologyType.LINEAR:
                    print(f"    Layout: Linear ({topology.dimensions[0]} LEDs)")

                print(f"    Zones: {topology.zones}")
                print()

        print("=" * 70)

    @staticmethod
    def _get_device_type_name(device_type: DeviceType) -> str:
        """Get human-readable device type name."""
        type_map = {
            DeviceType.MOTHERBOARD: "Motherboard",
            DeviceType.DRAM: "RAM",
            DeviceType.GPU: "Graphics Card",
            DeviceType.COOLER: "Cooler",
            DeviceType.LEDSTRIP: "LED Strip",
            DeviceType.KEYBOARD: "Keyboard",
            DeviceType.MOUSE: "Mouse",
            DeviceType.MOUSEMAT: "Mouse Mat",
            DeviceType.HEADSET: "Headset",
            DeviceType.HEADSET_STAND: "Headset Stand",
            DeviceType.GAMEPAD: "Gamepad",
            DeviceType.LIGHT: "Light",
            DeviceType.SPEAKER: "Speaker",
            DeviceType.VIRTUAL: "Virtual",
            DeviceType.UNKNOWN: "Unknown"
        }
        return type_map.get(device_type, "Unknown")
