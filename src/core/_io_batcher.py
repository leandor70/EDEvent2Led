"""
IO Batcher - Serializes LED frame writes to hardware.

This module provides the _IOBatcher class that intercepts apply_color_map()
calls from effect threads, buffers the resulting color arrays, and flushes
them in LED-count order (largest device first) within the render loop thread.
"""

import threading
import time
from typing import Dict, Tuple, Any, List


class _IOBatcher:
    """
    Collects LED frames posted by effect threads and sends them in a single
    ordered burst from the render-loop thread.

    Ordering: devices with more LEDs are sent first so that the keyboard
    (typically 105 LEDs) always leads and is visually in sync with smaller
    devices rather than lagging behind them.
    """

    def __init__(self):
        self._frames: Dict[str, Tuple[int, Any, list]] = {}
        self._lock = threading.Lock()

        self._disconnect_detected = False
        self._last_error_time = 0.0
        self._error_cooldown = 0.5

        self._recent_errors: List[Tuple[str, Exception]] = []

    def post(self, device_id: str, led_count: int, device, colors: list):
        """Called from an effect thread to register a new frame."""
        with self._lock:
            self._frames[device_id] = (led_count, device, colors)

    def flush(self, fast: bool = True, sync_colors: bool = False) -> int:
        """
        Send all buffered frames sorted by led_count descending.
        Must be called from the render-loop thread only.
        Returns the number of frames sent.
        """
        if self._disconnect_detected:
            elapsed = time.time() - self._last_error_time
            if elapsed < self._error_cooldown:
                with self._lock:
                    self._frames.clear()
                return 0
            else:
                self._disconnect_detected = False

        with self._lock:
            if not self._frames:
                return 0
            frames = sorted(self._frames.values(), key=lambda x: x[0], reverse=True)
            self._frames.clear()

        sent = 0
        for led_count, device, colors in frames:
            try:
                if sync_colors:
                    device._set_device_colors(colors, fast=True)
                    n = min(len(colors), len(device.colors))
                    for i in range(n):
                        device.colors[i] = colors[i]
                else:
                    device._set_device_colors(colors, fast=fast)
                sent += 1
            except Exception as e:
                from utils.openrgb_client import OpenRGBDisconnected

                dev_name = getattr(device, "name", "?")
                dev_leds = len(getattr(device, "leds", []))

                if isinstance(
                    e,
                    (OpenRGBDisconnected, ConnectionAbortedError, ConnectionResetError),
                ):
                    self._disconnect_detected = True
                    self._last_error_time = time.time()
                    print(
                        f"[Renderer] Disconnect detected | device='{dev_name}' | "
                        f"Skipping flush for {self._error_cooldown}s"
                    )

                    try:
                        from api.settings_api import invalidate_ping_cache

                        invalidate_ping_cache()
                    except Exception:
                        pass

                    self._recent_errors.append((dev_name, e))
                    continue

                print(
                    f"[Renderer] IOBatcher flush error"
                    f" | device='{dev_name}' leds={dev_leds}"
                    f" | colors_len={len(colors)}"
                    f" | exc={type(e).__name__}: {repr(e)}"
                )
        return sent

    def discard(self, device_id: str):
        """Remove any pending frame for a device (e.g. on effect cancel)."""
        with self._lock:
            self._frames.pop(device_id, None)

    def get_and_clear_recent_errors(self) -> List[Tuple[str, Exception]]:
        """
        Get and clear recent errors from flush operations.
        Returns list of (device_id/name, exception) tuples.
        """
        with self._lock:
            errors = self._recent_errors.copy()
            self._recent_errors.clear()
            return errors

    def reset_disconnect_state(self):
        """Reset disconnect detection state (called on reconnection)."""
        self._disconnect_detected = False
        self._recent_errors.clear()
