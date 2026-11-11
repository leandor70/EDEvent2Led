"""
Built-in client for the OpenRGB SDK server (TCP, default port 6742).

Written from the public protocol description of the OpenRGB SDK
(https://gitlab.com/CalcProgrammer1/OpenRGB/-/wikis/OpenRGB-SDK-Documentation).
The protocol core is shared with EDAmbilight (same author). It replaces the
openrgb-python library, so ED:Event2Led does not bundle third-party GPL code.

The public API is the subset of openrgb-python that ED:Event2Led uses, with
the same names and the same packets on the wire (verified byte for byte by
tools/test_openrgb_client.py against packets recorded from openrgb-python):

    OpenRGBClient(address, port, name)   .devices  .ee_devices  .update()  .ping()
    Device   .set_colors(colors, fast)  .set_color(color, fast)  .set_mode(name|index|Mode)
             .set_custom_mode()  .update()  .show()  .clear()
    Zone     .set_colors(colors, fast)  .set_color(color, fast)  .matrix_map (None = empty cell)
    LED      .set_color(color, fast)  .id (device-wide index)
    RGBColor(red, green, blue)   DeviceType   ZoneType   ModeColors   OpenRGBDisconnected

Differences from openrgb-python, on purpose:
  * The plugin list is never requested (an unknown plugin crashed the library).
  * Device.set_color() does not re-read the device afterwards: it is on the
    effects path, and the re-read cost a full round trip on every call.
  * Replies are matched on command AND device index, so a late reply can never
    be taken for the answer to a different request.

Performance: color payloads are packed with a precompiled struct per LED count
(about 2.5x faster than packing color by color), each packet goes out with a
single sendall(), and TCP_NODELAY is set so a frame is never held back.
All socket I/O is serialized by one lock: safe to call from several threads.

Packet: 16-byte header "ORGB" | device index u32 | command u32 | payload size u32,
then the payload. Everything is little-endian.
"""

from __future__ import annotations

import colorsys
import socket
import struct
import threading
import time
from enum import IntEnum
from itertools import chain
from typing import Dict, List, NamedTuple, Optional, Sequence, Union

DEFAULT_PORT = 6742
CLIENT_NAME = "ED:Event2Led"

# Highest protocol version this client can parse (same as openrgb-python 0.3.8).
# The server answers with the lower of the two, so newer servers still work.
MAX_PROTOCOL_VERSION = 4

_MAGIC = b"ORGB"
_HEADER = struct.Struct("<4sIII")
_U32 = struct.Struct("<I")
_I32 = struct.Struct("<i")
_U16 = struct.Struct("<H")

CMD_REQUEST_CONTROLLER_COUNT = 0
CMD_REQUEST_CONTROLLER_DATA = 1
CMD_REQUEST_PROTOCOL_VERSION = 40
CMD_SET_CLIENT_NAME = 50
CMD_DEVICE_LIST_UPDATED = 51
CMD_RGBCONTROLLER_UPDATELEDS = 1050
CMD_RGBCONTROLLER_UPDATEZONELEDS = 1051
CMD_RGBCONTROLLER_UPDATESINGLELED = 1052
CMD_RGBCONTROLLER_SETCUSTOMMODE = 1100
CMD_RGBCONTROLLER_UPDATEMODE = 1101
CMD_RGBCONTROLLER_SAVEMODE = 1102

NO_LED = 0xFFFFFFFF          # empty cell of a zone matrix on the wire

# Mode flags (which optional mode fields are meaningful)
_HAS_SPEED = 1 << 0
_HAS_DIRECTION = (1 << 1) | (1 << 2) | (1 << 3)     # LR, UD, HV
_HAS_BRIGHTNESS = 1 << 4


# ── Errors ─────────────────────────────────────────────────────────────────────


class OpenRGBError(Exception):
    """Protocol problem with the OpenRGB server."""


class OpenRGBDisconnected(OpenRGBError, ConnectionError):
    """The connection to the OpenRGB server is closed or lost."""


# ── Enums and value types ──────────────────────────────────────────────────────


class DeviceType(IntEnum):
    MOTHERBOARD = 0
    DRAM = 1
    GPU = 2
    COOLER = 3
    LEDSTRIP = 4
    KEYBOARD = 5
    MOUSE = 6
    MOUSEMAT = 7
    HEADSET = 8
    HEADSET_STAND = 9
    GAMEPAD = 10
    LIGHT = 11
    SPEAKER = 12
    VIRTUAL = 13
    STORAGE = 14
    CASE = 15
    MICROPHONE = 16
    ACCESSORY = 17
    KEYPAD = 18
    UNKNOWN = 19

    @classmethod
    def _missing_(cls, value):
        # A type added by a newer OpenRGB must not break the device list.
        return cls.UNKNOWN


class ZoneType(IntEnum):
    SINGLE = 0
    LINEAR = 1
    MATRIX = 2
    LINEAR_LOOP = 3
    MATRIX_LOOP_X = 4
    MATRIX_LOOP_Y = 5
    SEGMENTED = 6

    @classmethod
    def _missing_(cls, value):
        return cls.LINEAR


class ModeColors(IntEnum):
    NONE = 0
    PER_LED = 1
    MODE_SPECIFIC = 2
    RANDOM = 3

    @classmethod
    def _missing_(cls, value):
        return cls.NONE


class RGBColor(NamedTuple):
    """A color. A NamedTuple: cheap to create, compares equal to (r, g, b)."""
    red: int
    green: int
    blue: int

    def pack(self, version: int = 0) -> bytes:
        return _COLOR.pack(self.red, self.green, self.blue)

    @classmethod
    def fromHSV(cls, hue: float, saturation: float, value: float) -> "RGBColor":
        return cls(*(round(i * 255) for i in colorsys.hsv_to_rgb(hue / 360, saturation / 100, value / 100)))

    @classmethod
    def fromHEX(cls, hex: str) -> "RGBColor":
        h = hex.lstrip("#")
        return cls(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


_COLOR = struct.Struct("<BBBx")
_COLOR_STRUCTS: Dict[int, struct.Struct] = {}


def _pack_colors(colors: Sequence[Sequence[int]]) -> bytes:
    """n colors -> 4n bytes (R, G, B, padding). Raises struct.error outside 0..255."""
    n = len(colors)
    s = _COLOR_STRUCTS.get(n)
    if s is None:
        s = _COLOR_STRUCTS[n] = struct.Struct("<" + "BBBx" * n)
    return s.pack(*chain.from_iterable(colors))


def _pack_string(text: str) -> bytes:
    raw = text.encode("utf-8") + b"\x00"
    return _U16.pack(len(raw)) + raw


# ── Data model ─────────────────────────────────────────────────────────────────


class Metadata:
    __slots__ = ("vendor", "description", "version", "serial", "location")

    def __init__(self, vendor="", description="", version="", serial="", location="") -> None:
        self.vendor = vendor
        self.description = description
        self.version = version
        self.serial = serial
        self.location = location


class Segment:
    __slots__ = ("id", "name", "type", "start_idx", "leds_count")

    def __init__(self, id: int, name: str, type_: int, start_idx: int, leds_count: int) -> None:
        self.id = id
        self.name = name
        self.type = ZoneType(type_)
        self.start_idx = start_idx
        self.leds_count = leds_count


class Mode:
    """A device mode. Attribute names as openrgb-python's ModeData."""

    __slots__ = ("id", "name", "value", "flags", "speed_min", "speed_max",
                 "brightness_min", "brightness_max", "colors_min", "colors_max",
                 "speed", "brightness", "direction", "color_mode", "colors")

    def __init__(self, id, name, value, flags, speed_min, speed_max, brightness_min,
                 brightness_max, colors_min, colors_max, speed, brightness, direction,
                 color_mode, colors) -> None:
        self.id = id
        self.name = name
        self.value = value
        self.flags = flags
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.colors_min = colors_min
        self.colors_max = colors_max
        self.speed = speed
        self.brightness = brightness
        self.direction = direction
        self.color_mode = color_mode
        self.colors = colors

    def pack(self, version: int) -> bytes:
        """Payload of UPDATEMODE / SAVEMODE: size, index, then the mode description."""
        out = bytearray()
        out += _I32.pack(self.id)
        out += _pack_string(self.name)
        out += struct.pack("<iIII", self.value, self.flags, self.speed_min or 0, self.speed_max or 0)
        if version >= 3:
            out += struct.pack("<II", self.brightness_min or 0, self.brightness_max or 0)
        out += struct.pack("<III", self.colors_min or 0, self.colors_max or 0, self.speed or 0)
        if version >= 3:
            out += _U32.pack(self.brightness or 0)
        out += struct.pack("<II", self.direction or 0, int(self.color_mode))
        colors = self.colors or []
        out += _U16.pack(len(colors)) + _pack_colors(colors)
        return _U32.pack(len(out) + 4) + bytes(out)


class LED:
    """One LED. `id` is its index in the whole device (as in openrgb-python)."""

    __slots__ = ("id", "name", "value", "_device")

    def __init__(self, device: "Device", id: int, name: str, value: int) -> None:
        self._device = device
        self.id = id
        self.name = name
        self.value = value

    @property
    def device_id(self) -> int:
        return self._device.id

    @property
    def colors(self) -> List[RGBColor]:
        return [self._device.colors[self.id]]

    def set_color(self, color: Sequence[int], fast: bool = False) -> None:
        dev = self._device
        dev._client._send(dev.id, CMD_RGBCONTROLLER_UPDATESINGLELED,
                          _I32.pack(self.id) + _COLOR.pack(color[0], color[1], color[2]))
        if not fast:
            dev.update()

    def update(self) -> None:
        self._device.update()


class Zone:
    """A zone: a run of consecutive LEDs of the device."""

    def __init__(self, device: "Device", id: int) -> None:
        self._device = device
        self.id = id
        self.name = ""
        self.type = ZoneType.SINGLE
        self.leds_min = 0
        self.leds_max = 0
        self.start_idx = 0
        self.leds: List[LED] = []
        self.mat_height: Optional[int] = None
        self.mat_width: Optional[int] = None
        # matrix_map[row][col] = LED index inside the zone, None for an empty cell
        self.matrix_map: Optional[List[List[Optional[int]]]] = None
        self.segments: Optional[List[Segment]] = None

    @property
    def device_id(self) -> int:
        return self._device.id

    @property
    def colors(self) -> List[RGBColor]:
        return self._device.colors[self.start_idx:self.start_idx + len(self.leds)]

    def set_colors(self, colors: Sequence[Sequence[int]], fast: bool = False) -> None:
        n = len(self.leds)
        if len(colors) != n:
            raise IndexError("Number of colors doesn't match number of LEDs in the zone")
        body = struct.pack("<iH", self.id, n) + _pack_colors(colors)
        dev = self._device
        dev._client._send(dev.id, CMD_RGBCONTROLLER_UPDATEZONELEDS, _U32.pack(len(body) + 4) + body)
        if not fast:
            dev.update()

    def set_color(self, color: Sequence[int], fast: bool = False) -> None:
        self.set_colors([color] * len(self.leds), fast)

    def update(self) -> None:
        self._device.update()


class Device:
    """One RGB controller as reported by the server."""

    def __init__(self, client: "OpenRGBClient", index: int) -> None:
        self._client = client
        self.id = index
        self.type = DeviceType.UNKNOWN
        self.name = ""
        self.metadata = Metadata()
        self.modes: List[Mode] = []
        self.active_mode = 0
        self.zones: List[Zone] = []
        self.leds: List[LED] = []
        self.colors: List[RGBColor] = []
        self._colors: List[RGBColor] = []   # last state read from the server (for show())

    def __repr__(self) -> str:
        return f"Device(name={self.name}, id={self.id})"

    @property
    def device_id(self) -> int:
        return self.id

    # ── Colors ─────────────────────────────────────────────────────────────────

    def set_colors(self, colors: Sequence[Sequence[int]], fast: bool = False) -> None:
        """Set every LED. In a mode with its own colors, set the mode colors instead.
        In a mode without colors (NONE / RANDOM) nothing is sent, like openrgb-python."""
        mode = self.modes[self.active_mode] if self.modes else None
        color_mode = mode.color_mode if mode is not None else ModeColors.PER_LED
        if color_mode == ModeColors.PER_LED:
            self._set_device_colors(colors, fast)
        elif color_mode == ModeColors.MODE_SPECIFIC:
            lo, hi = mode.colors_min or 0, mode.colors_max or 0
            if not lo <= len(colors) <= hi:
                raise ValueError(f"{self.name!r}: mode {mode.name!r} takes "
                                 f"{lo}..{hi} colors, got {len(colors)}")
            mode.colors = [RGBColor(*c[:3]) for c in colors]
            self.set_mode(mode)

    def set_color(self, color: Sequence[int], fast: bool = False) -> None:
        """Set the whole device to one color. Never re-reads the device (see module doc)."""
        mode = self.modes[self.active_mode] if self.modes else None
        color_mode = mode.color_mode if mode is not None else ModeColors.PER_LED
        if color_mode == ModeColors.PER_LED:
            self._send_leds([color] * len(self.leds))
        elif color_mode == ModeColors.MODE_SPECIFIC:
            mode.colors = [RGBColor(*color[:3])] * (mode.colors_max or 0)
            self.set_mode(mode)

    def _set_device_colors(self, colors: Sequence[Sequence[int]], fast: bool = False) -> None:
        """Write every LED whatever the active mode (openrgb-python's private method,
        used by the IOBatcher on the per-frame path)."""
        self._send_leds(colors)
        if not fast:
            self.update()

    def _send_leds(self, colors: Sequence[Sequence[int]]) -> None:
        n = len(self.leds)
        if len(colors) != n:
            raise IndexError("Number of colors doesn't match number of LEDs")
        body = _U16.pack(n) + _pack_colors(colors)
        self._client._send(self.id, CMD_RGBCONTROLLER_UPDATELEDS, _U32.pack(len(body) + 4) + body)

    def show(self, fast: bool = False, force: bool = False) -> None:
        """Send the changes made to `colors` since the last read (openrgb-python semantics)."""
        if len(self.colors) != len(self._colors):
            raise ValueError(f"`colors` has {len(self.colors)} items, expected {len(self._colors)}")
        if force:
            self.set_colors(self.colors, fast=True)
        else:
            changed = [i for i, c in enumerate(self.colors) if c != self._colors[i]]
            if not changed:
                return
            if len(changed) == 1:
                i = changed[0]
                self.leds[i].set_color(self.colors[i], fast=True)
            else:
                self.set_colors(self.colors, fast=True)
        self._colors = self.colors[:]
        if not fast:
            self.update()

    def clear(self) -> None:
        self.set_color((0, 0, 0))

    # ── Modes ──────────────────────────────────────────────────────────────────

    def set_mode(self, mode: Union[str, int, Mode], save: bool = False) -> None:
        """Activate a mode by name (case-insensitive), index or Mode object, then
        re-read the device until the server confirms it (up to 5 tries, as openrgb-python)."""
        if isinstance(mode, str):
            wanted = mode.lower()
            found = next((m for m in self.modes if m.name.lower() == wanted), None)
            if found is None:
                raise ValueError(f"Mode `{mode}` not found for device `{self.name}`")
            mode = found
        elif isinstance(mode, int):
            mode = self.modes[mode]
        elif not isinstance(mode, Mode):
            raise TypeError(f"mode must be a name, an index or a Mode, not {type(mode).__name__}")
        data = mode.pack(self._client.protocol_version)
        self._client._send(self.id, CMD_RGBCONTROLLER_UPDATEMODE, data)
        if save:
            self._client._send(self.id, CMD_RGBCONTROLLER_SAVEMODE, data)
        for _ in range(5):
            self.update()
            if self.active_mode == mode.id:
                return
            time.sleep(0.05)
        self.active_mode = mode.id

    def set_custom_mode(self) -> None:
        """Let the server pick the mode with per-LED control, then apply it."""
        self._client._send(self.id, CMD_RGBCONTROLLER_SETCUSTOMMODE, b"")
        self.update()
        self.set_mode(self.active_mode)

    # ── State ──────────────────────────────────────────────────────────────────

    def update(self) -> None:
        """Re-read this device from the server. Objects (zones, LEDs) are updated
        in place, so references held elsewhere stay valid."""
        self._client._read_device(self)


# ── Wire format: controller data ───────────────────────────────────────────────


class _Reader:
    """Sequential little-endian reader over a controller-data payload."""

    __slots__ = ("_d", "pos")

    def __init__(self, data: bytes) -> None:
        self._d = data
        self.pos = 0

    def _check(self, size: int) -> None:
        if self.pos + size > len(self._d):
            raise OpenRGBError("Truncated data from the OpenRGB server")

    def u16(self) -> int:
        self._check(2)
        (v,) = _U16.unpack_from(self._d, self.pos)
        self.pos += 2
        return v

    def u32(self) -> int:
        self._check(4)
        (v,) = _U32.unpack_from(self._d, self.pos)
        self.pos += 4
        return v

    def i32(self) -> int:
        self._check(4)
        (v,) = _I32.unpack_from(self._d, self.pos)
        self.pos += 4
        return v

    def u32_array(self, n: int):
        self._check(4 * n)
        v = struct.unpack_from(f"<{n}I", self._d, self.pos)
        self.pos += 4 * n
        return v

    def string(self) -> str:
        """u16 length (terminator included) followed by that many bytes."""
        n = self.u16()
        self._check(n)
        raw = self._d[self.pos:self.pos + n]
        self.pos += n
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

    def colors(self, n: int) -> List[RGBColor]:
        self._check(4 * n)
        d, p = self._d, self.pos
        self.pos += 4 * n
        return [RGBColor(d[i], d[i + 1], d[i + 2]) for i in range(p, p + 4 * n, 4)]


def _read_mode(r: _Reader, idx: int, version: int) -> Mode:
    name = r.string()
    value = r.i32()
    flags = r.u32()
    speed_min = r.u32()
    speed_max = r.u32()
    brightness_min = brightness_max = None
    if version >= 3:
        brightness_min = r.u32()
        brightness_max = r.u32()
    colors_min = r.u32()
    colors_max = r.u32()
    speed = r.u32()
    brightness = r.u32() if version >= 3 else None
    direction = r.u32()
    color_mode = ModeColors(r.u32())
    colors = r.colors(r.u16())
    # Fields the flags do not declare carry garbage from the server: drop them
    # (None), so they are sent back as 0, exactly like openrgb-python.
    if not flags & _HAS_DIRECTION:
        direction = None
    if not flags & _HAS_SPEED:
        speed_min = speed_max = speed = None
    if not flags & _HAS_BRIGHTNESS or version < 3:
        brightness_min = brightness_max = brightness = None
    if not colors:
        colors = colors_min = colors_max = None
    return Mode(idx, name, value, flags, speed_min, speed_max, brightness_min, brightness_max,
                colors_min, colors_max, speed, brightness, direction, color_mode, colors)


def _read_zone(r: _Reader, zone: Zone, version: int) -> int:
    """Fill `zone` in place; return its LED count."""
    zone.name = r.string()
    zone.type = ZoneType(r.i32())
    zone.leds_min = r.u32()
    zone.leds_max = r.u32()
    count = r.u32()
    if r.u16():                                   # matrix block size
        h = r.u32()
        w = r.u32()
        cells = r.u32_array(h * w)
        zone.mat_height, zone.mat_width = h, w
        zone.matrix_map = [[None if c == NO_LED else c for c in cells[row * w:(row + 1) * w]]
                           for row in range(h)]
    else:
        zone.mat_height = zone.mat_width = None
        zone.matrix_map = None
    if version >= 4:
        zone.segments = [Segment(i, r.string(), r.i32(), r.u32(), r.u32()) for i in range(r.u16())]
    else:
        zone.segments = None
    return count


def _parse_into(dev: Device, data: bytes, version: int) -> None:
    """Fill `dev` from a REQUEST_CONTROLLER_DATA reply, reusing its zone/LED objects."""
    r = _Reader(data)
    r.u32()                                       # total size, includes itself
    dev.type = DeviceType(r.i32())
    dev.name = r.string()
    vendor = r.string() if version >= 1 else ""
    description = r.string()
    fw_version = r.string()
    serial = r.string()
    location = r.string()
    dev.metadata = Metadata(vendor, description, fw_version, serial, location)

    num_modes = r.u16()
    dev.active_mode = r.i32()
    dev.modes = [_read_mode(r, i, version) for i in range(num_modes)]

    num_zones = r.u16()
    zones = dev.zones[:num_zones]
    zones += [Zone(dev, i) for i in range(len(zones), num_zones)]
    counts = [_read_zone(r, z, version) for z in zones]

    num_leds = r.u16()
    leds = dev.leds[:num_leds]
    for i in range(num_leds):
        name = r.string()
        value = r.u32()
        if i < len(leds):
            leds[i].name, leds[i].value = name, value
        else:
            leds.append(LED(dev, i, name, value))

    dev.colors = r.colors(r.u16())
    dev._colors = dev.colors[:]
    dev.zones = zones
    dev.leds = leds

    # A zone owns the next `count` LEDs of the device, in order.
    start = 0
    for zone, count in zip(zones, counts):
        zone.start_idx = start
        zone.leds = leds[start:start + count]
        start += count


# ── Client ─────────────────────────────────────────────────────────────────────


class OpenRGBClient:
    """Connection to an OpenRGB SDK server. Connecting reads the device list."""

    def __init__(self, address: str = "127.0.0.1", port: int = DEFAULT_PORT,
                 name: str = CLIENT_NAME, protocol_version: Optional[int] = None,
                 timeout: float = 5.0) -> None:
        self.address = address
        self.port = int(port)
        self.name = name
        self.timeout = timeout
        self._max_version = MAX_PROTOCOL_VERSION if protocol_version is None \
            else min(int(protocol_version), MAX_PROTOCOL_VERSION)
        self._protocol_version = 0
        self.devices: List[Device] = []
        self.device_list_changed = False      # the server announced a hardware change
        self._lock = threading.Lock()
        self._sock: Optional[socket.socket] = None
        self.connect()

    def __repr__(self) -> str:
        return f"OpenRGBClient(address={self.address}, port={self.port}, name={self.name})"

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        self.disconnect()
        try:
            sock = socket.create_connection((self.address, self.port), timeout=self.timeout)
        except OSError as exc:
            raise OpenRGBDisconnected(
                f"Cannot connect to OpenRGB at {self.address}:{self.port}: {exc}") from exc
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self.timeout)
        self._sock = sock
        try:
            self._negotiate_version()
            self._send(0, CMD_SET_CLIENT_NAME, self.name.encode("utf-8") + b"\x00")
            self.update()
        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    close = disconnect

    @property
    def connected(self) -> bool:
        return self._sock is not None

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    def __enter__(self) -> "OpenRGBClient":
        return self

    def __exit__(self, *exc) -> None:
        self.disconnect()

    def ping(self, timeout: float = 2.0) -> int:
        """Ask the server for its controller count: proves the connection is alive.
        Raises OpenRGBDisconnected otherwise."""
        payload = self._request(0, CMD_REQUEST_CONTROLLER_COUNT, b"", timeout=timeout)
        return _U32.unpack_from(payload)[0]

    # ── Devices ────────────────────────────────────────────────────────────────

    @property
    def ee_devices(self) -> List[Device]:
        """Devices with a "Direct" mode (suitable for frame-by-frame effects).
        Local filter: does NOT contact the server (use ping() for that)."""
        return [d for d in self.devices for m in d.modes if m.name.lower() == "direct"]

    def update(self) -> None:
        """Read the device list again. Existing Device objects are updated in place."""
        count = self.ping(timeout=self.timeout)
        devices = self.devices[:count]
        devices += [Device(self, i) for i in range(len(devices), count)]
        for dev in devices:
            self._read_device(dev)
        self.devices = devices
        self.device_list_changed = False

    def show(self, fast: bool = False, force: bool = False) -> None:
        for dev in self.devices:
            dev.show(True, force)
        if not fast:
            self.update()

    def clear(self) -> None:
        for dev in self.devices:
            dev.clear()

    def _read_device(self, dev: Device) -> None:
        request = _U32.pack(self._protocol_version) if self._protocol_version >= 1 else b""
        data = self._request(dev.id, CMD_REQUEST_CONTROLLER_DATA, request)
        _parse_into(dev, data, self._protocol_version)

    def _negotiate_version(self) -> None:
        """Offer our highest version; a server too old to answer means version 0."""
        try:
            payload = self._request(0, CMD_REQUEST_PROTOCOL_VERSION, _U32.pack(self._max_version),
                                    timeout=1.0, timeout_is_disconnect=False)
            self._protocol_version = min(_U32.unpack_from(payload)[0], self._max_version)
        except socket.timeout:
            self._protocol_version = 0

    # ── Packets ────────────────────────────────────────────────────────────────

    def _send(self, device_index: int, command: int, payload: bytes) -> None:
        """Send one packet (no reply expected). Single sendall: header and payload together."""
        data = _HEADER.pack(_MAGIC, device_index, command, len(payload)) + payload
        with self._lock:
            sock = self._sock
            if sock is None:
                raise OpenRGBDisconnected("Connection to OpenRGB is closed")
            try:
                sock.sendall(data)
            except OSError as exc:
                self._drop()
                raise OpenRGBDisconnected(f"Lost connection to OpenRGB: {exc}") from exc

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise OpenRGBDisconnected("OpenRGB closed the connection")
            buf += chunk
        return bytes(buf)

    def _request(self, device_index: int, command: int, payload: bytes,
                 timeout: Optional[float] = None, timeout_is_disconnect: bool = True) -> bytes:
        """Send a request and return the payload of its reply (same command and device).

        Packets the server sends on its own (device list changed) are noted and
        skipped while waiting.
        """
        data = _HEADER.pack(_MAGIC, device_index, command, len(payload)) + payload
        with self._lock:
            sock = self._sock
            if sock is None:
                raise OpenRGBDisconnected("Connection to OpenRGB is closed")
            if timeout is not None:
                sock.settimeout(timeout)
            try:
                sock.sendall(data)
                while True:
                    magic, idx, cmd, size = _HEADER.unpack(self._recv_exact(sock, _HEADER.size))
                    if magic != _MAGIC:
                        raise OpenRGBError("Unexpected data from the OpenRGB server")
                    body = self._recv_exact(sock, size) if size else b""
                    if cmd == CMD_DEVICE_LIST_UPDATED:
                        self.device_list_changed = True
                    elif cmd == command and idx == device_index:
                        return body
            except socket.timeout:
                if timeout_is_disconnect:
                    self._drop()
                    raise OpenRGBDisconnected("OpenRGB did not answer in time")
                raise
            except OpenRGBDisconnected:
                self._drop()
                raise
            except OSError as exc:
                self._drop()
                raise OpenRGBDisconnected(f"Lost connection to OpenRGB: {exc}") from exc
            finally:
                if timeout is not None and self._sock is not None:
                    self._sock.settimeout(self.timeout)

    def _drop(self) -> None:
        """Close a broken socket (caller holds the lock). Later calls raise OpenRGBDisconnected."""
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
