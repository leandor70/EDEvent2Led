"""
openrgb_safe.py
Safe wrappers for OpenRGB operations with validation and error handling.
Prevents common hardware compatibility issues across different RGB devices.
"""

from utils.openrgb_client import RGBColor, DeviceType
from typing import List, Optional, Tuple
import time


class DeviceSafetyError(Exception):
    """Raised when device validation fails"""
    pass


def validate_led_count(device, requested_count: int, operation: str = "operation") -> bool:
    """
    Validate that requested LED count matches device capability.

    Args:
        device: OpenRGB device instance
        requested_count: Number of LEDs we're trying to control
        operation: Description of operation for error message

    Returns:
        bool: True if valid

    Raises:
        DeviceSafetyError: If validation fails
    """
    actual_count = len(device.leds)

    if requested_count != actual_count:
        raise DeviceSafetyError(
            f"{operation} failed: Requested {requested_count} LEDs but device "
            f"'{device.name}' has {actual_count} LEDs"
        )

    return True


def validate_color_array(colors: List, expected_count: int, operation: str = "operation") -> bool:
    """
    Validate color array before sending to device.

    Args:
        colors: List of RGBColor objects
        expected_count: Expected number of colors
        operation: Description of operation

    Returns:
        bool: True if valid

    Raises:
        DeviceSafetyError: If validation fails
    """
    if len(colors) != expected_count:
        raise DeviceSafetyError(
            f"{operation} failed: Color array length {len(colors)} != expected {expected_count}"
        )

    # Verify all elements are RGBColor objects
    for i, color in enumerate(colors):
        if not isinstance(color, RGBColor):
            raise DeviceSafetyError(
                f"{operation} failed: Element {i} is {type(color).__name__}, "
                f"expected RGBColor. Use RGBColor(r, g, b) instead of tuples."
            )

    return True


def safe_set_colors(device, colors: List[RGBColor], fast: bool = True,
                   operation: str = "set_colors") -> bool:
    """
    Safely set device colors with validation.

    Args:
        device: OpenRGB device instance
        colors: List of RGBColor objects
        fast: Use fast mode (default True)
        operation: Operation description for logging

    Returns:
        bool: True if successful

    Raises:
        DeviceSafetyError: If validation fails
        Exception: If OpenRGB operation fails
    """
    try:
        # Validate LED count
        validate_led_count(device, len(colors), operation)

        # Validate color array
        validate_color_array(colors, len(device.leds), operation)

        # Execute operation
        device.set_colors(colors, fast=fast)
        return True

    except DeviceSafetyError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Wrap OpenRGB errors with context
        raise Exception(
            f"{operation} failed for device '{device.name}': {type(e).__name__}: {str(e)}"
        ) from e


def safe_get_colors(device, operation: str = "get_colors") -> List[RGBColor]:
    """
    Safely get device colors with fallback.

    Args:
        device: OpenRGB device instance
        operation: Operation description

    Returns:
        List[RGBColor]: Current device colors, or black fallback
    """
    try:
        colors = list(device.colors)
        led_count = len(device.leds)

        # Pad with black if colors array is shorter than LED count
        if len(colors) < led_count:
            print(f"[WARNING] {device.name}: colors array ({len(colors)}) < LED count ({led_count}), padding with black")
            colors += [RGBColor(0, 0, 0)] * (led_count - len(colors))

        return colors[:led_count]  # Trim if longer

    except Exception as e:
        led_count = len(device.leds)
        print(f"[ERROR] {operation} failed for '{device.name}': {e}, returning black array")
        return [RGBColor(0, 0, 0)] * led_count


def check_device_mode_support(device, mode_name: str) -> bool:
    """
    Check if device supports a specific mode.

    Args:
        device: OpenRGB device instance
        mode_name: Mode name to check (e.g., "Direct", "Static")

    Returns:
        bool: True if mode is supported
    """
    try:
        available_modes = [mode.name for mode in device.modes]
        return mode_name in available_modes
    except Exception as e:
        print(f"[ERROR] Failed to check modes for '{device.name}': {e}")
        return False


def safe_set_mode(device, mode_name: str, operation: str = "set_mode") -> bool:
    """
    Safely set device mode with validation.

    Args:
        device: OpenRGB device instance
        mode_name: Target mode name
        operation: Operation description

    Returns:
        bool: True if successful

    Raises:
        DeviceSafetyError: If mode not supported
    """
    if not check_device_mode_support(device, mode_name):
        available = [m.name for m in device.modes]
        raise DeviceSafetyError(
            f"{operation} failed: Device '{device.name}' does not support mode '{mode_name}'. "
            f"Available modes: {', '.join(available)}"
        )

    try:
        device.set_mode(mode_name)
        return True
    except Exception as e:
        raise Exception(
            f"{operation} failed for device '{device.name}': {type(e).__name__}: {str(e)}"
        ) from e


def create_color_array(r: int, g: int, b: int, count: int) -> List[RGBColor]:
    """
    Safely create uniform color array.

    Args:
        r, g, b: RGB values (0-255)
        count: Number of LEDs

    Returns:
        List[RGBColor]: Array of identical colors
    """
    # Clamp values to valid range
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))

    color = RGBColor(r, g, b)
    return [color] * count


def retry_on_disconnect(max_retries: int = 2, delay: float = 0.1, reconnect_callback=None):
    """
    Decorator with automatic retry on OpenRGBDisconnected.

    Args:
        max_retries: Maximum retry attempts (default: 2)
        delay: Delay between retries in seconds (default: 0.1)
        reconnect_callback: Optional function to call before retry
                           Signature: () -> bool (True if reconnected)

    Example:
        @retry_on_disconnect(max_retries=2, reconnect_callback=_reconnect)
        def get_device_count(client):
            return len(client.devices)
    """
    from utils.openrgb_client import OpenRGBDisconnected

    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except OpenRGBDisconnected as e:
                    if attempt == max_retries:
                        raise  # Propagate to Tier 2

                    print(f"[OpenRGBSafe] Disconnect, retry {attempt+1}/{max_retries}")

                    if reconnect_callback:
                        try:
                            reconnect_callback()
                        except Exception as err:
                            print(f"[OpenRGBSafe] Reconnect callback failed: {err}")

                    time.sleep(delay)
                except Exception:
                    raise  # Don't retry non-disconnect errors

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# ============================================================================
# DEVICE TYPE HELPERS
# ============================================================================

def is_keyboard(device) -> bool:
    """Check if device is a keyboard"""
    return device.type == DeviceType.KEYBOARD


def is_mouse(device) -> bool:
    """Check if device is a mouse"""
    return device.type == DeviceType.MOUSE


def is_strip(device) -> bool:
    """Check if device is an LED strip"""
    return device.type in [DeviceType.LEDSTRIP, DeviceType.DRAM]


def get_safe_device_info(device) -> dict:
    """
    Safely extract device information without triggering errors.

    Args:
        device: OpenRGB device instance

    Returns:
        dict: Device information with safe defaults
    """
    try:
        return {
            'name': device.name,
            'type': device.type.name if hasattr(device.type, 'name') else str(device.type),
            'led_count': len(device.leds),
            'zone_count': len(device.zones) if hasattr(device, 'zones') else 0,
            'mode_count': len(device.modes) if hasattr(device, 'modes') else 0,
            'current_mode': device.active_mode.name if hasattr(device, 'active_mode') else 'Unknown',
            'supports_direct': check_device_mode_support(device, 'Direct')
        }
    except Exception as e:
        return {
            'name': getattr(device, 'name', 'Unknown'),
            'error': str(e)
        }


print("[OpenRGBSafe] Safety utilities module loaded")
