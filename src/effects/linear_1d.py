"""
1D Linear Effects for devices like RAM modules, LED strips, mice, etc.
Provides spatial effects along a linear LED array.
"""
import math
import json
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Dict, Any
from utils.openrgb_client import RGBColor
from utils.openrgb_safe import safe_get_colors, safe_set_colors, create_color_array, DeviceSafetyError
from utils.color_utils import hsv_to_rgb_normalized
from effects import topology_geometry as geo


class Linear1D:
    """
    Represents a linear (1D) LED array.
    Enables spatial effects like waves, scans, gradients, etc.
    """

    def __init__(self, device, led_count: int, global_idx: int = 0, device_key: str = None):
        """
        Initialize 1D linear LED controller.

        Args:
            device: OpenRGB device object
            led_count: Number of LEDs in linear array
            global_idx: Device position in UnifiedEffectManager.devices
            device_key: Key of this device in device_topologies.json (utils.device_keys);
                        defaults to the bare '<name>::linear' key
        """
        self.device = device
        self.led_count = led_count
        self._global_idx = global_idx
        self._device_key = device_key or f"{getattr(device, 'name', 'unknown')}::linear"
        # IO intercept: when set, apply_color_map calls this instead of device.set_colors.
        # Used by VisualEffectRenderer to batch and serialize hardware I/O.
        self._frame_intercept = None  # Optional[Callable[[List[RGBColor]], None]]

        # Load device topology for world coordinate calculations
        self._topology = None
        self._zones = []
        self._global_bbox = None
        self._drawn_bbox = None
        self._load_topology()

    def set_led(self, index: int, color: Tuple[int, int, int]):
        """
        Set color for a specific LED.

        Args:
            index: LED index (0-based)
            color: RGB tuple (0-255)
        """
        if 0 <= index < self.led_count:
            try:
                colors = safe_get_colors(self.device, operation="linear_1d:set_led")
                colors[index] = RGBColor(*color)
                safe_set_colors(self.device, colors, fast=True, operation="linear_1d:set_led")
            except DeviceSafetyError as e:
                print(f"[ERROR] Linear1D set_led validation failed: {e}")

    def get_led_color(self, index: int) -> Optional[Tuple[int, int, int]]:
        """
        Get current color of a specific LED.

        Args:
            index: LED index (0-based)

        Returns:
            RGB tuple (0-255) or None if index invalid
        """
        if 0 <= index < self.led_count:
            try:
                colors = safe_get_colors(self.device, operation="linear_1d:get_led_color")
                if index < len(colors):
                    color = colors[index]
                    return (color.red, color.green, color.blue)
            except DeviceSafetyError as e:
                print(f"[ERROR] Linear1D get_led_color validation failed: {e}")
        return None

    def set_all_leds(self, color: Tuple[int, int, int]):
        """
        Set all LEDs to the same color.

        Args:
            color: RGB tuple (0-255)
        """
        if self._frame_intercept is not None:
            # Renderer will handle validation
            colors = create_color_array(color[0], color[1], color[2], self.led_count)
            self._frame_intercept(colors)
        else:
            # Direct mode: validate before sending
            try:
                colors = create_color_array(color[0], color[1], color[2], self.led_count)
                safe_set_colors(self.device, colors, fast=True, operation="linear_1d:set_all_leds")
            except DeviceSafetyError as e:
                print(f"[ERROR] Linear1D set_all_leds validation failed: {e}")

    def apply_color_map(self, color_map: dict):
        """
        Apply a dictionary of LED colors.

        Args:
            color_map: Dict mapping LED index -> RGB color tuple
        """
        # Safely get current colors with fallback
        colors = safe_get_colors(self.device, operation="linear_1d:apply_color_map")

        for led_idx, color in color_map.items():
            if 0 <= led_idx < len(colors):
                colors[led_idx] = RGBColor(*color)

        if self._frame_intercept is not None:
            # Renderer will handle validation via IOBatcher
            self._frame_intercept(colors)
        else:
            # Direct mode: validate before sending
            try:
                safe_set_colors(self.device, colors, fast=True, operation="linear_1d:apply_color_map")
            except DeviceSafetyError as e:
                print(f"[ERROR] Linear1D color validation failed: {e}")

    # ===== 1D EFFECT GENERATORS =====

    def generate_solid(self, color: Tuple[int, int, int]) -> dict:
        """
        Generate color map for solid color.

        Args:
            color: RGB color

        Returns:
            Dict mapping LED index -> color
        """
        return {i: color for i in range(self.led_count)}

    def generate_gradient(self, color1: Tuple[int, int, int],
                         color2: Tuple[int, int, int],
                         reverse: bool = False) -> dict:
        """
        Generate color map for a gradient from color1 to color2.

        Args:
            color1: Start RGB color
            color2: End RGB color
            reverse: If True, gradient goes from color2 to color1

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for i in range(self.led_count):
            factor = i / (self.led_count - 1) if self.led_count > 1 else 0

            if reverse:
                factor = 1 - factor

            color = (
                int(color1[0] + (color2[0] - color1[0]) * factor),
                int(color1[1] + (color2[1] - color1[1]) * factor),
                int(color1[2] + (color2[2] - color1[2]) * factor)
            )
            color_map[i] = color

        return color_map

    def generate_wave(self, time: float, color: Tuple[int, int, int] = (255, 128, 0),
                     wavelength: float = 4.0, speed: float = 1.0) -> dict:
        """
        Generate color map for a sine wave.

        Args:
            time: Current time in seconds
            color: Base RGB color
            wavelength: Wave period (in LED units)
            speed: Wave propagation speed

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for i in range(self.led_count):
            phase = (i / wavelength - time * speed) * 2 * math.pi
            intensity = (math.sin(phase) + 1) / 2  # Range 0-1

            dimmed_color = (
                int(color[0] * intensity),
                int(color[1] * intensity),
                int(color[2] * intensity)
            )
            color_map[i] = dimmed_color

        return color_map

    def generate_scanner(self, position: float, color: Tuple[int, int, int],
                        width: float = 3.0, tail_length: int = 5) -> dict:
        """
        Generate color map for a "Cylon eye" scanner effect.

        Args:
            position: Current position (0 to led_count)
            color: RGB color
            width: Width of the bright center
            tail_length: Length of trailing fade

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}

        for i in range(self.led_count):
            distance = abs(i - position)

            if distance <= width / 2:
                # Bright center
                intensity = 1.0
            elif distance <= width / 2 + tail_length:
                # Fading tail
                tail_dist = distance - width / 2
                intensity = 1.0 - (tail_dist / tail_length)
            else:
                intensity = 0.0

            if intensity > 0:
                dimmed_color = (
                    int(color[0] * intensity),
                    int(color[1] * intensity),
                    int(color[2] * intensity)
                )
                color_map[i] = dimmed_color

        return color_map

    def generate_chase(self, position: int, color: Tuple[int, int, int],
                      spacing: int = 3, count: int = 3) -> dict:
        """
        Generate color map for a chase effect (multiple moving dots).

        Args:
            position: Current position offset
            color: RGB color
            spacing: Space between dots
            count: Number of dots

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}

        for dot in range(count):
            led_idx = (position + dot * spacing) % self.led_count
            color_map[led_idx] = color

        return color_map

    def generate_rainbow(self, offset: float = 0.0) -> dict:
        """
        Generate color map for a rainbow gradient.

        Args:
            offset: Color offset (0-1) for animation

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}

        for i in range(self.led_count):
            hue = ((i / self.led_count) + offset) % 1.0
            color = hsv_to_rgb_normalized(hue, 1.0, 1.0)
            color_map[i] = color

        return color_map

    def generate_sparkle(self, active_leds: List[int], color: Tuple[int, int, int]) -> dict:
        """
        Generate color map for sparkle effect.

        Args:
            active_leds: List of LED indices to light up
            color: RGB color

        Returns:
            Dict mapping LED index -> color
        """
        return {i: color for i in active_leds if 0 <= i < self.led_count}

    def generate_fill(self, fill_amount: float, color: Tuple[int, int, int],
                     direction: str = 'forward') -> dict:
        """
        Generate color map for a fill/progress bar effect.

        Args:
            fill_amount: Amount to fill (0.0 to 1.0)
            color: RGB color
            direction: 'forward' or 'reverse'

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        filled_count = int(self.led_count * fill_amount)

        if direction == 'forward':
            for i in range(filled_count):
                color_map[i] = color
        else:  # reverse
            for i in range(self.led_count - filled_count, self.led_count):
                color_map[i] = color

        return color_map

    def generate_center_out(self, position: float, color: Tuple[int, int, int]) -> dict:
        """
        Generate color map for effect expanding from center.

        Args:
            position: Expansion progress (0.0 to 1.0)
            color: RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        center = self.led_count / 2
        max_distance = center

        expand_distance = position * max_distance

        for i in range(self.led_count):
            distance = abs(i - center)
            if distance <= expand_distance:
                # Fade based on distance
                intensity = 1.0 - (distance / max_distance) * 0.5
                dimmed_color = (
                    int(color[0] * intensity),
                    int(color[1] * intensity),
                    int(color[2] * intensity)
                )
                color_map[i] = dimmed_color

        return color_map

    def generate_pulse_from_center(self, position: float, color: Tuple[int, int, int],
                                   width: float = 5.0) -> dict:
        """
        Generate color map for pulse expanding from center.

        Args:
            position: Pulse position (0.0 to 1.0)
            color: RGB color
            width: Pulse width

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        center = self.led_count / 2
        max_distance = center

        pulse_pos = position * max_distance

        for i in range(self.led_count):
            distance_from_center = abs(i - center)
            distance_from_pulse = abs(distance_from_center - pulse_pos)

            if distance_from_pulse <= width:
                intensity = 1.0 - (distance_from_pulse / width)
                dimmed_color = (
                    int(color[0] * intensity),
                    int(color[1] * intensity),
                    int(color[2] * intensity)
                )
                color_map[i] = dimmed_color

        return color_map

    def generate_custom(self, generator_func: Callable[[int], Tuple[int, int, int]]) -> dict:
        """
        Generate color map using a custom function.

        Args:
            generator_func: Function that takes LED index and returns RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for i in range(self.led_count):
            color = generator_func(i)
            color_map[i] = color
        return color_map

    # ===== TOPOLOGY SUPPORT FOR WORLD COORDINATES =====

    def _load_topology(self):
        """
        Load device topology from device_topologies.json.
        This enables world coordinate calculations for multi-zone LINEAR devices.
        """
        topology_file = Path("config/device_topologies.json")
        if not topology_file.exists():
            # No topology file = fallback to simple 1D linear (all LEDs in a row)
            self._zones = [{
                'zone_index': 0,
                'led_count': self.led_count,
                'position': {'x': 0, 'y': 0},
                'rotation': 0
            }]
            self._calculate_global_bbox()
            return

        try:
            with open(topology_file, 'r') as f:
                data = json.load(f)

            # Find topology for this device: exact device key only. A fallback to
            # the bare key would hand the first device's layout to its twins.
            device_name = self.device.name if hasattr(self.device, 'name') else 'unknown'
            self._topology = data.get('topologies', {}).get(self._device_key)

            if self._topology:
                self._zones = self._topology.get('zones', [])
                self._calculate_global_bbox()
                return

            # Device not in topology file = fallback
            self._zones = [{
                'zone_index': 0,
                'led_count': self.led_count,
                'position': {'x': 0, 'y': 0},
                'rotation': 0
            }]
            self._calculate_global_bbox()

        except Exception as e:
            print(f"[WARNING] Failed to load topology for {device_name}: {e}")
            # Fallback to simple linear
            self._zones = [{
                'zone_index': 0,
                'led_count': self.led_count,
                'position': {'x': 0, 'y': 0},
                'rotation': 0
            }]
            self._calculate_global_bbox()

    def _calculate_global_bbox(self):
        """Calculate global bounding box for all zones."""
        """Due riquadri, per due usi diversi (entrambi dalla geometria unica):

        _global_bbox: estensione dei CENTRI dei LED. E' la "tela" degli effetti:
            normalizzazioni, griglie (Fire), orientamento (Aurora). Cosi' il primo e
            l'ultimo LED di una striscia stanno a 0 e 1, e una striscia orizzontale
            ha altezza 0.
        _drawn_bbox: corner dei rettangoli zona disegnati, identico a
            calculateBoundingBox() dell'editor. Serve dove una percentuale e' stata
            scelta guardando l'editor (centro effetto)."""
        default = {'min_x': 0, 'max_x': 1, 'min_y': 0, 'max_y': 1}
        pts = [p for z in self._zones for p in geo.led_world_positions(z)]
        if not pts:
            self._global_bbox = dict(default)
            self._drawn_bbox = dict(default)
            return

        self._global_bbox = {
            'min_x': min(p[0] for p in pts),
            'max_x': max(p[0] for p in pts),
            'min_y': min(p[1] for p in pts),
            'max_y': max(p[1] for p in pts),
        }
        min_x, max_x, min_y, max_y = geo.scene_bbox(self._zones)
        self._drawn_bbox = {'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y}

    def get_effect_center(self) -> Optional[Tuple[float, float]]:
        """
        Get custom effect center from device topology, if configured.

        Returns:
            (world_x, world_y) tuple in world coordinates, or None if not configured

        Note: Reloads topology from file to ensure fresh configuration.
        """
        # Reload topology to get latest configuration from file
        # This ensures changes made in Topology Editor are immediately reflected
        self._load_topology()

        # Check if topology is loaded and is a dict
        if not isinstance(self._topology, dict):
            return None

        # Check if effect_center is configured
        center_config = self._topology.get('effect_center', {})
        if not isinstance(center_config, dict):
            return None

        # Check if enabled flag is True
        if not center_config.get('enabled', False):
            return None

        # Read percentages (default 50% if missing)
        percent_x = center_config.get('x', 50.0)
        percent_y = center_config.get('y', 50.0)

        # Percentuali scelte nell'editor: riquadro disegnato (come calculateBoundingBox)
        bbox = self._drawn_bbox
        if not bbox:
            return None

        # Normalize percentages to [0,1]
        norm_x = max(0.0, min(1.0, percent_x / 100.0))
        norm_y = max(0.0, min(1.0, percent_y / 100.0))

        # Map to world coordinates
        width = bbox['max_x'] - bbox['min_x']
        height = bbox['max_y'] - bbox['min_y']
        world_x = bbox['min_x'] + norm_x * width
        world_y = bbox['min_y'] + norm_y * height

        return (world_x, world_y)

    def get_led_world_position(self, zone_index: int, led_index: int) -> Tuple[int, int]:
        """
        Get world coordinates (X, Y) for a LED in a specific zone.

        Args:
            zone_index: Zone/segment index
            led_index: LED index within the zone (0-based)

        Returns:
            (world_x, world_y) tuple
        """
        if zone_index >= len(self._zones):
            return (0, 0)

        # Centro del LED come e' disegnato nell'editor: rotazione continua e
        # direction (reverse = LED 0 all'estremo lontano). Vedi topology_geometry.
        return geo.led_world_position(self._zones[zone_index], led_index)

    def get_global_bbox(self) -> Dict[str, int]:
        """
        Get global bounding box for all zones.

        Returns:
            Dict with keys: min_x, max_x, min_y, max_y
        """
        return self._global_bbox if self._global_bbox else {'min_x': 0, 'max_x': 1, 'min_y': 0, 'max_y': 1}

    def get_zone_and_local_index(self, global_led_index: int) -> Tuple[int, int]:
        """
        Convert global LED index to (zone_index, local_led_index).

        Args:
            global_led_index: LED index across entire device (0 to led_count-1)

        Returns:
            (zone_index, local_led_index) tuple
        """
        cumulative = 0
        for zone_idx, zone in enumerate(self._zones):
            zone_led_count = zone['led_count']
            if global_led_index < cumulative + zone_led_count:
                local_idx = global_led_index - cumulative
                return (zone_idx, local_idx)
            cumulative += zone_led_count

        # Fallback: out of range = last zone, last LED
        if self._zones:
            last_zone_idx = len(self._zones) - 1
            last_led_idx = self._zones[last_zone_idx]['led_count'] - 1
            return (last_zone_idx, last_led_idx)
        return (0, 0)

    def get_zone_rotation(self, zone_idx: int) -> int:
        """
        Get rotation angle of a specific zone.

        Args:
            zone_idx: Zone index

        Returns:
            Rotation angle in degrees (0, 90, 180, 270)
        """
        if 0 <= zone_idx < len(self._zones):
            return self._zones[zone_idx].get('rotation', 0)
        return 0
