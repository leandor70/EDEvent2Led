#!/usr/bin/env python3
"""
POC Ambilight — screen edge sampling -> LED strip via OpenRGB.
UI web di configurazione live su http://localhost:8765

  cd <root progetto>
  python tools/poc_ambilight/ambilight_poc.py
  # poi apri http://localhost:8765 nel browser
"""

import json
import time
import ctypes
import threading
import argparse
import numpy as np
import eel
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ── CONFIGURAZIONE ────────────────────────────────────────────────────────────

ZONE_SCREEN_MAP = {
    "MonitorRight":  {"edge": "right",  "reversed": False},
    "MonitorTop":    {"edge": "top",    "reversed": True},
    "MonitorLeft":   {"edge": "left",   "reversed": True},
    "MonitorBottom": {"edge": "bottom", "reversed": False},
    "Desktop":       {"edge": "bottom", "reversed": False},
}

# Stato condiviso thread cattura <-> Eel (GIL protegge letture/scritture semplici)
_config: dict = {
    "fps":              15,
    "strategy":         "adaptive_smooth",
    "depth":            10.0,
    "saturation_boost": 1.4,
    "ema_alpha":        0.35,
    "scene_cut":        60.0,
    "adaptive_min":     3.0,
    "adaptive_max":     20.0,
    "preview_only":     False,
    "zones_enabled":    {},
}

_status: dict = {
    "running":     False,
    "actual_fps":  0.0,
    "frame_count": 0,
    "zone_colors": {},
}

_stop_event                          = threading.Event()
_capture_thread: threading.Thread | None = None
_zones_list:     list                = []
_total_leds:     int                 = 0
_frame_colors:   list                = []
_capturer_ref                        = None
_device_ref                          = None
_capturer_name:  str                 = "—"
_auto_switch:    bool                = False


# ── LETTURA CONFIG ────────────────────────────────────────────────────────────

def load_settings() -> dict:
    with open(ROOT / "config" / "settings.json", encoding="utf-8") as f:
        return json.load(f)


def _led_world_positions(zone: dict) -> list[tuple[float, float]]:
    x0      = zone["position"]["x"]
    y0      = zone["position"]["y"]
    spacing = zone.get("led_spacing", 1.0)
    rot     = zone.get("rotation", 0)
    dx = {0: spacing, 90: 0,        180: -spacing, 270: 0       }.get(rot, spacing)
    dy = {0: 0,       90: spacing,  180: 0,         270: -spacing}.get(rot, 0)
    return [(x0 + i * dx, y0 + i * dy) for i in range(zone["led_count"])]


def load_monitor_zones() -> tuple[str, list[dict], int]:
    with open(ROOT / "config" / "device_topologies.json", encoding="utf-8") as f:
        data = json.load(f)

    for dev_id, topology in data.get("topologies", {}).items():
        all_zones = sorted(topology.get("zones", []), key=lambda z: z["zone_index"])
        if not all_zones:
            continue

        offset = 0
        offset_map: dict[int, int] = {}
        for zone in all_zones:
            offset_map[zone["zone_index"]] = offset
            offset += zone["led_count"]
        total_leds = offset

        frame_zones = [z for z in all_zones if z.get("name", "").startswith("Monitor")]
        if frame_zones:
            all_pts   = [pt for z in frame_zones for pt in _led_world_positions(z)]
            mon_x_min = min(p[0] for p in all_pts)
            mon_x_max = max(p[0] for p in all_pts)
            mon_y_min = min(p[1] for p in all_pts)
            mon_y_max = max(p[1] for p in all_pts)
        else:
            mon_x_min, mon_x_max, mon_y_min, mon_y_max = 0, 100, 0, 100

        monitor_zones = []
        for zone in all_zones:
            name = zone.get("name", "")
            if name not in ZONE_SCREEN_MAP:
                continue

            mapping  = ZONE_SCREEN_MAP[name]
            edge     = mapping["edge"]
            spacing  = zone.get("led_spacing", 1.0)
            led_pts  = _led_world_positions(zone)

            if edge in ("top", "bottom"):
                in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)
                            if mon_x_min <= x <= mon_x_max]
                if not in_range:
                    print(f"  [WARNING] Zone '{name}': nessun LED dentro bbox monitor "
                          f"(x=[{mon_x_min:.1f},{mon_x_max:.1f}]) — uso tutti i {len(led_pts)} LED.")
                    in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)]
                xs           = [x for _, x, _ in in_range]
                x_lo, x_hi   = min(xs), max(xs)
                mon_span     = mon_x_max - mon_x_min
                screen_start = max(0.0, (x_lo - spacing / 2 - mon_x_min) / mon_span)
                screen_end   = min(1.0, (x_hi + spacing / 2 - mon_x_min) / mon_span)
            else:
                in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)
                            if mon_y_min <= y <= mon_y_max]
                if not in_range:
                    print(f"  [WARNING] Zone '{name}': nessun LED dentro bbox monitor "
                          f"(y=[{mon_y_min:.1f},{mon_y_max:.1f}]) — uso tutti i {len(led_pts)} LED.")
                    in_range = [(i, x, y) for i, (x, y) in enumerate(led_pts)]
                ys           = [y for _, _, y in in_range]
                y_lo, y_hi   = min(ys), max(ys)
                mon_span     = mon_y_max - mon_y_min
                screen_start = max(0.0, (y_lo - spacing / 2 - mon_y_min) / mon_span)
                screen_end   = min(1.0, (y_hi + spacing / 2 - mon_y_min) / mon_span)

            led_start = in_range[0][0]
            led_end   = in_range[-1][0] + 1

            monitor_zones.append({
                "name":         name,
                "zone_index":   zone["zone_index"],
                "led_count":    zone["led_count"],
                "led_offset":   offset_map[zone["zone_index"]],
                "led_start":    led_start,
                "led_end":      led_end,
                "screen_start": screen_start,
                "screen_end":   screen_end,
                "edge":         edge,
                "reversed":     mapping["reversed"],
            })

        if monitor_zones:
            print(f"[Ambilight] Device: {dev_id} ({total_leds} LED totali)")
            print(f"[Ambilight] Monitor bbox: x=[{mon_x_min:.1f},{mon_x_max:.1f}] "
                  f"y=[{mon_y_min:.1f},{mon_y_max:.1f}]")
            for z in monitor_zones:
                active   = z["led_end"] - z["led_start"]
                skipped  = z["led_count"] - active
                skip_str = f"  ({skipped} fuori monitor)" if skipped else ""
                print(f"  Zone {z['zone_index']:2d}: {z['name']:<16} "
                      f"LED [{z['led_start']}-{z['led_end']-1}] ({active} attivi){skip_str}  "
                      f"screen=[{z['screen_start']:.2f},{z['screen_end']:.2f}]  "
                      f"-> {z['edge']}{' rev' if z['reversed'] else ''}")
            return dev_id, monitor_zones, total_leds

    raise RuntimeError(
        "Nessuna zona monitor trovata in device_topologies.json.\n"
        f"Zone riconosciute: {list(ZONE_SCREEN_MAP.keys())}"
    )


# ── SCREEN CAPTURE ────────────────────────────────────────────────────────────

class DxcamCapturer:
    """DXGI Desktop Duplication — funziona anche in exclusive fullscreen."""
    _RECOVERABLE = ("0x887a0026", "access lost", "access_lost", "output-change")

    def __init__(self, fps: int):
        import dxcam
        self._dxcam = dxcam
        self._fps   = fps
        self._cam   = dxcam.create(output_color="BGR")
        self._cam.start(target_fps=fps)
        print("[Ambilight] Capturer: dxcam (DXGI)")

    def grab(self):
        try:
            return self._cam.get_latest_frame()
        except Exception as exc:
            if any(t in str(exc).lower() for t in self._RECOVERABLE):
                return self._recover()
            raise

    def _recover(self):
        print("[Ambilight] DXGI access lost — recupero...")
        try:
            self._cam.stop()
        except Exception:
            pass
        time.sleep(0.5)
        for attempt in range(1, 4):
            try:
                self._cam = self._dxcam.create(output_color="BGR")
                self._cam.start(target_fps=self._fps)
                print(f"[Ambilight] DXGI recuperato ({attempt}/3).")
                _prev_colors.clear()
                return None
            except Exception as exc:
                print(f"[Ambilight] Recupero {attempt}/3 fallito: {exc}")
                time.sleep(1.0)
        raise RuntimeError("[Ambilight] DXGI: impossibile recuperare dopo 3 tentativi.")

    def update_fps(self, fps: int):
        if fps == self._fps:
            return
        try:
            self._cam.stop()
        except Exception:
            pass
        self._fps = fps
        self._cam = self._dxcam.create(output_color="BGR")
        self._cam.start(target_fps=fps)

    def stop(self):
        try:
            self._cam.stop()
        except Exception:
            pass


class MssCapturer:
    """GDI screenshot — funziona con borderless windowed, non con exclusive FS."""
    def __init__(self):
        import mss
        self._sct     = mss.MSS()
        self._monitor = self._sct.monitors[1]
        print(f"[Ambilight] Capturer: mss ({self._monitor['width']}x{self._monitor['height']})")

    def grab(self):
        shot = self._sct.grab(self._monitor)
        arr  = np.frombuffer(shot.bgra, dtype=np.uint8).reshape((shot.height, shot.width, 4))
        return arr[:, :, :3]

    def update_fps(self, fps: int):
        pass

    def stop(self):
        self._sct.close()


class WGCCapturer:
    """Windows.Graphics.Capture — coesiste con Chrome e GPU apps (Win10 1903+).
    Usa il compositor DWM: nessun lock diretto sull'output GPU."""

    def __init__(self, fps: int):
        from windows_capture import WindowsCapture

        self._fps    = fps
        self._latest: np.ndarray | None = None
        self._lock   = threading.Lock()

        cap = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            monitor_index=1,
            minimum_update_interval=33,  # ~30 fps max dal callback; rate limit reale è nel loop
        )

        @cap.event
        def on_frame_arrived(frame, _capture_control):
            # frame.frame_buffer è una VIEW in memoria ctypes gestita da Rust:
            # diventa invalida quando il callback ritorna → .copy() obbligatorio
            bgr = frame.frame_buffer[:, :, :3].copy()
            with self._lock:
                self._latest = bgr

        @cap.event
        def on_closed():
            pass

        # start_free_threaded: threading gestito internamente; ritorna CaptureControl.stop()
        self._ctrl = cap.start_free_threaded()

        # Aspetta primo frame (max 3s)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            with self._lock:
                if self._latest is not None:
                    break
            time.sleep(0.05)

        print("[Ambilight] Capturer: WGC (Windows.Graphics.Capture)")

    def grab(self) -> np.ndarray | None:
        with self._lock:
            return self._latest

    def update_fps(self, fps: int):
        self._fps = fps  # rate limit reale è nel capture loop; WGC usa minimum_update_interval

    def stop(self):
        try:
            self._ctrl.stop()
        except Exception:
            pass


def make_capturer(fps: int, preferred: str = "auto"):
    """
    preferred: "auto" | "wgc" | "dxcam" | "mss"
      auto  — WGC → dxcam → mss (default)
      wgc   — Windows.Graphics.Capture: Chrome-safe, no exclusive fullscreen OpenGL
      dxcam — DXGI Desktop Duplication: tutto incluso exclusive FS, ma conflitto Chrome GPU
      mss   — GDI BitBlt: CPU-only, no exclusive FS, sempre sicuro
    """
    global _capturer_name

    def _try_wgc():
        global _capturer_name
        c = WGCCapturer(fps)
        _capturer_name = "WGC"
        return c

    def _try_dxcam():
        global _capturer_name
        c = DxcamCapturer(fps)
        _capturer_name = "DXGI"
        return c

    def _use_mss():
        global _capturer_name
        _capturer_name = "mss"
        return MssCapturer()

    if preferred == "wgc":
        try:
            return _try_wgc()
        except Exception as exc:
            print(f"[Ambilight] WGC non disponibile ({exc}). Provo dxcam.")
    elif preferred == "dxcam":
        try:
            return _try_dxcam()
        except Exception as exc:
            print(f"[Ambilight] dxcam non disponibile ({exc}). Fallback mss.")
        return _use_mss()
    elif preferred == "mss":
        return _use_mss()

    # auto: WGC → dxcam → mss
    try:
        return _try_wgc()
    except ImportError:
        print("[Ambilight] windows-capture non installato — provo dxcam.")
    except Exception as exc:
        print(f"[Ambilight] WGC init fallita ({exc}) — provo dxcam.")
    try:
        return _try_dxcam()
    except ImportError:
        print("[Ambilight] dxcam non installato — fallback mss (no exclusive FS).")
    except Exception as exc:
        print(f"[Ambilight] dxcam init fallita ({exc}) — fallback mss.")
    return _use_mss()


# ── STRATEGIE DI CAMPIONAMENTO ────────────────────────────────────────────────

STRATEGIES: dict[str, str] = {
    "mean":            "Media RGB — semplice e veloce, tende a desaturare",
    "percentile":      "Percentile 80% — bias ai colori brillanti, ignora il nero",
    "dominant":        "Colore dominante — mediana RGB, robusta agli outlier cromatici",
    "hsv":             "Media HSV — preserva la saturazione percepita",
    "adaptive":        "Adaptive depth — profondita auto basata su varianza locale",
    "smooth":          "Percentile+EMA — percentile con smoothing temporale",
    "adaptive_smooth": "Adaptive+EMA — depth auto + smoothing temporale [migliore]",
}

_prev_colors: dict[str, list] = {}


def _sample_segment(seg_2d: np.ndarray, strategy: str) -> tuple[int, int, int]:
    """Estrae il colore rappresentativo da un segmento float32. Per 'hsv' lo spazio e' gia' HSV."""
    pixels = seg_2d.reshape(-1, 3)
    if len(pixels) == 0:
        return (0, 0, 0)

    if strategy == "mean":
        bgr = pixels.mean(axis=0)

    elif strategy in ("percentile", "smooth", "adaptive", "adaptive_smooth"):
        lums = 0.2126 * pixels[:, 2] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 0]
        k    = int(len(lums) * 0.80)
        idx  = np.argpartition(lums, k)[k]
        bgr  = pixels[idx]

    elif strategy == "dominant":
        bgr = np.median(pixels, axis=0)

    elif strategy == "hsv":
        import cv2
        theta  = pixels[:, 0] * np.pi / 90.0
        h_mean = np.arctan2(np.sin(theta).mean(), np.cos(theta).mean()) * 90.0 / np.pi % 180
        s_mean = pixels[:, 1].mean()
        v_mean = pixels[:, 2].mean()
        bgr_u8 = cv2.cvtColor(
            np.array([[[int(h_mean), int(s_mean), int(v_mean)]]], dtype=np.uint8),
            cv2.COLOR_HSV2BGR
        )[0, 0]
        return (int(bgr_u8[2]), int(bgr_u8[1]), int(bgr_u8[0]))

    else:
        bgr = pixels.mean(axis=0)

    return (int(bgr[2]), int(bgr[1]), int(bgr[0]))


def _apply_temporal_smooth(
    zone_name: str,
    new_colors: list[tuple[int, int, int]],
    alpha: float = 0.35,
    cut_threshold: float = 60.0,
) -> list[tuple[int, int, int]]:
    prev = _prev_colors.get(zone_name)
    if prev is None or len(prev) != len(new_colors):
        _prev_colors[zone_name] = new_colors
        return new_colors

    avg_delta = sum(
        (abs(n[0]-p[0]) + abs(n[1]-p[1]) + abs(n[2]-p[2])) / 3
        for n, p in zip(new_colors, prev)
    ) / len(new_colors)

    if avg_delta > cut_threshold:
        result = new_colors
    else:
        result = [
            (
                min(255, max(0, int(p[0] + alpha * (n[0] - p[0])))),
                min(255, max(0, int(p[1] + alpha * (n[1] - p[1])))),
                min(255, max(0, int(p[2] + alpha * (n[2] - p[2])))),
            )
            for n, p in zip(new_colors, prev)
        ]

    _prev_colors[zone_name] = result
    return result


def _adaptive_depth(
    frame_bgr: np.ndarray,
    edge: str,
    screen_start: float,
    screen_end: float,
    min_pct: float = 0.03,
    max_pct: float = 0.20,
) -> float:
    h, w  = frame_bgr.shape[:2]
    probe = max(1, int(min(h, w) * 0.03))
    if edge in ("top", "bottom"):
        x0, x1 = int(w * screen_start), max(int(w * screen_start) + 1, int(w * screen_end))
        outer  = frame_bgr[:probe, x0:x1, :] if edge == "top" else frame_bgr[-probe:, x0:x1, :]
    else:
        y0, y1 = int(h * screen_start), max(int(h * screen_start) + 1, int(h * screen_end))
        outer  = frame_bgr[y0:y1, :probe, :] if edge == "left" else frame_bgr[y0:y1, -probe:, :]
    norm = min(1.0, float(outer.std()) / 80.0)
    return max_pct - norm * (max_pct - min_pct)


def sample_edge(
    frame_bgr: np.ndarray,
    edge: str,
    led_count: int,
    reversed_dir: bool,
    depth_pct: float,
    screen_start: float  = 0.0,
    screen_end: float    = 1.0,
    strategy: str        = "mean",
    zone_name: str       = "",
    cfg: dict | None     = None,
) -> list[tuple[int, int, int]]:
    if cfg is None:
        cfg = {}
    h, w = frame_bgr.shape[:2]

    if strategy in ("adaptive", "adaptive_smooth"):
        depth_pct = _adaptive_depth(
            frame_bgr, edge, screen_start, screen_end,
            min_pct=cfg.get("adaptive_min", 3.0) / 100.0,
            max_pct=cfg.get("adaptive_max", 20.0) / 100.0,
        )

    depth = max(1, int(min(h, w) * depth_pct))

    if edge in ("top", "bottom"):
        x0    = int(w * screen_start)
        x1    = max(x0 + 1, int(w * screen_end))
        strip = frame_bgr[:depth, x0:x1, :] if edge == "top" else frame_bgr[-depth:, x0:x1, :]
        axis  = 1
    else:
        y0    = int(h * screen_start)
        y1    = max(y0 + 1, int(h * screen_end))
        strip = frame_bgr[y0:y1, :depth, :] if edge == "left" else frame_bgr[y0:y1, -depth:, :]
        axis  = 0

    if strategy == "hsv":
        import cv2
        strip_proc = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV).astype(np.float32)
    else:
        strip_proc = strip.astype(np.float32)

    segs   = np.array_split(strip_proc, led_count, axis=axis)
    colors = [_sample_segment(seg, strategy) for seg in segs]

    if strategy in ("smooth", "adaptive_smooth") and zone_name:
        colors = _apply_temporal_smooth(
            zone_name, colors,
            alpha=cfg.get("ema_alpha", 0.35),
            cut_threshold=cfg.get("scene_cut", 60.0),
        )

    return colors[::-1] if reversed_dir else colors


def boost_saturation(
    colors: list[tuple[int, int, int]],
    factor: float,
) -> list[tuple[int, int, int]]:
    result = []
    for r, g, b in colors:
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        result.append((
            min(255, max(0, int(lum + (r - lum) * factor))),
            min(255, max(0, int(lum + (g - lum) * factor))),
            min(255, max(0, int(lum + (b - lum) * factor))),
        ))
    return result


# ── OPENRGB ───────────────────────────────────────────────────────────────────

def _openrgb_client_module():
    # Built-in OpenRGB client of ED:Event2Led (src/utils/openrgb_client.py)
    import sys
    src = str(Path(__file__).resolve().parents[2] / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from utils import openrgb_client
    return openrgb_client


def connect_openrgb(host: str, port: int, dev_id_key: str):
    OpenRGBClient = _openrgb_client_module().OpenRGBClient
    client    = OpenRGBClient(host, port)
    base_name = dev_id_key.split("::")[0]
    for device in client.devices:
        if device.name == base_name or base_name in device.name:
            print(f"[Ambilight] OpenRGB: '{device.name}' ({len(device.leds)} LED)")
            device.set_mode("direct")
            return client, device
    raise RuntimeError(
        f"Device '{base_name}' non trovato. Disponibili: {[d.name for d in client.devices]}"
    )


def apply_colors_to_device(device, frame_colors: list[tuple[int, int, int]]):
    RGBColor = _openrgb_client_module().RGBColor
    device.set_colors([RGBColor(r, g, b) for r, g, b in frame_colors])


# ── EEL API ──────────────────────────────────────────────────────────────────

@eel.expose
def get_config() -> dict:
    return dict(_config)


@eel.expose
def set_config(updates: dict):
    if "strategy" in updates and updates["strategy"] != _config.get("strategy"):
        _prev_colors.clear()
    _config.update(updates)


@eel.expose
def get_status() -> dict:
    return {
        "running":      _status["running"],
        "actual_fps":   _status["actual_fps"],
        "frame_count":  _status["frame_count"],
        "zone_colors":  _status["zone_colors"],
        "capturer":     _capturer_name,
    }


@eel.expose
def get_zones() -> list:
    return [
        {
            "name":      z["name"],
            "edge":      z["edge"],
            "led_count": z["led_end"] - z["led_start"],
            "enabled":   _config["zones_enabled"].get(z["name"], True),
        }
        for z in _zones_list
    ]


@eel.expose
def get_strategies() -> dict:
    return STRATEGIES


@eel.expose
def start_capture() -> dict:
    global _capture_thread
    if _status["running"]:
        return {"ok": False, "msg": "Gia in esecuzione"}
    _stop_event.clear()
    _prev_colors.clear()
    _capture_thread = threading.Thread(
        target=_capture_loop, daemon=True, name="ambilight-capture"
    )
    _capture_thread.start()
    return {"ok": True}


@eel.expose
def stop_capture() -> dict:
    _stop_event.set()
    return {"ok": True}


# ── AUTO CAPTURER SWITCHER ───────────────────────────────────────────────────

class _AutoSwitch:
    """Rileva frame congelati (exclusive fullscreen) e switcha WGC ↔ DXGI automaticamente."""
    STUCK_SECS  = 2.5   # frame diff sotto soglia per questo tempo → switch a DXGI
    TRIAL_SECS  = 2.0   # durata prova WGC dopo cambio finestra foreground
    DIFF_MIN    = 3.0   # avg pixel diff < soglia = frame "congelato"
    CHECK_EVERY = 8     # ogni N frame (a 15fps ≈ ogni 0.5s)

    def __init__(self):
        self.prev_sample:  np.ndarray | None = None
        self.stuck_since:  float | None      = None
        self.fg_at_switch: int               = 0
        self.trial_since:  float | None      = None
        self.mode:         str               = _capturer_name

    @staticmethod
    def _sample(frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        return frame[max(0, h // 2 - 75):h // 2 + 75,
                     max(0, w // 2 - 100):w // 2 + 100]

    def _swap(self, preferred: str) -> bool:
        global _capturer_ref
        old = _capturer_ref
        try:
            _capturer_ref    = make_capturer(_config.get("fps", 15), preferred=preferred)
            self.mode        = _capturer_name
            self.prev_sample = None
            self.stuck_since = None
            self.trial_since = None
            try:
                old.stop()
            except Exception:
                pass
            _prev_colors.clear()
            print(f"[Ambilight] Auto-capturer: -> {_capturer_name}")
            return True
        except Exception as exc:
            print(f"[Ambilight] Auto-capturer: switch '{preferred}' fallito: {exc}")
            return False

    def check(self, frame: np.ndarray, now: float) -> None:
        sample = self._sample(frame)

        if self.prev_sample is not None and self.prev_sample.shape == sample.shape:
            diff = float(np.abs(
                sample.astype(np.float32) - self.prev_sample.astype(np.float32)
            ).mean())

            if self.trial_since is not None:
                # WGC in prova: aspettiamo che i frame varino
                if diff >= self.DIFF_MIN:
                    # WGC riceve frame freschi → confermato, resta su WGC
                    self.trial_since = None
                    self.stuck_since = None
                elif now - self.trial_since >= self.TRIAL_SECS:
                    # Ancora congelato → torna a DXGI
                    if self._swap("dxcam"):
                        self.fg_at_switch = ctypes.windll.user32.GetForegroundWindow()

            elif self.mode == "WGC":
                if diff < self.DIFF_MIN:
                    if self.stuck_since is None:
                        self.stuck_since = now
                    elif now - self.stuck_since >= self.STUCK_SECS:
                        # Sospetto exclusive fullscreen → switch a DXGI
                        self.fg_at_switch = ctypes.windll.user32.GetForegroundWindow()
                        self._swap("dxcam")
                else:
                    self.stuck_since = None

            elif self.mode == "DXGI":
                fg = ctypes.windll.user32.GetForegroundWindow()
                if fg != 0 and fg != self.fg_at_switch:
                    # Finestra foreground cambiata → prova ritorno a WGC
                    if self._swap("wgc"):
                        self.trial_since = now

        self.prev_sample = sample.copy()


# ── CAPTURE LOOP ─────────────────────────────────────────────────────────────

def _capture_loop():
    global _frame_colors
    _status["running"]     = True
    _status["actual_fps"]  = 0.0
    _status["frame_count"] = 0
    _frame_colors = [(0, 0, 0)] * _total_leds

    _timer_ok = False
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        _timer_ok = True
    except AttributeError:
        pass

    auto            = _AutoSwitch() if _auto_switch else None
    local_frame_idx = 0

    try:
        while not _stop_event.is_set():
            t0  = time.perf_counter()
            cfg = dict(_config)   # snapshot atomico per questo frame

            frame = _capturer_ref.grab()
            if frame is None:
                _stop_event.wait(0.01)
                continue

            local_frame_idx += 1
            if auto is not None and local_frame_idx % _AutoSwitch.CHECK_EVERY == 0:
                auto.check(frame, t0)

            depth_pct = cfg.get("depth", 10.0) / 100.0
            strategy  = cfg.get("strategy", "adaptive_smooth")
            sat_boost = cfg.get("saturation_boost", 1.4)
            zones_ena = cfg.get("zones_enabled", {})
            zone_colors: dict[str, list] = {}

            for zone in _zones_list:
                if not zones_ena.get(zone["name"], True):
                    continue

                led_start = zone["led_start"]
                led_end   = zone["led_end"]
                active    = led_end - led_start

                colors = sample_edge(
                    frame,
                    edge         = zone["edge"],
                    led_count    = active,
                    reversed_dir = zone["reversed"],
                    depth_pct    = depth_pct,
                    screen_start = zone["screen_start"],
                    screen_end   = zone["screen_end"],
                    strategy     = strategy,
                    zone_name    = zone["name"],
                    cfg          = cfg,
                )

                if strategy != "hsv":
                    colors = boost_saturation(colors, sat_boost)

                zone_colors[zone["name"]] = colors
                off = zone["led_offset"] + led_start
                _frame_colors[off:off + active] = colors

            _status["zone_colors"] = zone_colors

            if _device_ref is not None and not cfg.get("preview_only", False):
                try:
                    apply_colors_to_device(_device_ref, _frame_colors)
                except Exception as exc:
                    print(f"[Ambilight] Errore invio LED: {exc}")

            elapsed = time.perf_counter() - t0
            if elapsed > 0:
                _status["actual_fps"] = round(
                    0.85 * _status["actual_fps"] + 0.15 / elapsed, 1
                )
            _status["frame_count"] += 1

            wait = 1.0 / cfg.get("fps", 15) - elapsed
            if wait > 0:
                _stop_event.wait(wait)

    finally:
        if _timer_ok:
            ctypes.windll.winmm.timeEndPeriod(1)
        _status["running"]    = False
        _status["actual_fps"] = 0.0
        if _device_ref is not None and not _config.get("preview_only", False):
            try:
                apply_colors_to_device(_device_ref, [(0, 0, 0)] * _total_leds)
            except Exception:
                pass
        print("[Ambilight] Loop fermato. LED spenti.")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def _on_browser_close(_page, sockets):
    if not sockets:
        _stop_event.set()


def main():
    global _zones_list, _total_leds, _capturer_ref, _device_ref, _capture_thread, _auto_switch

    parser = argparse.ArgumentParser(description="POC Ambilight — UI su http://localhost:8765")
    parser.add_argument("--preview",   action="store_true",
                        help="Non inviare ai LED (preview nel browser)")
    parser.add_argument("--fps",       type=int, default=15)
    parser.add_argument("--strategy",  choices=list(STRATEGIES.keys()), default="adaptive_smooth")
    parser.add_argument("--port",      type=int, default=8765)
    parser.add_argument("--autostart", action="store_true",
                        help="Avvia il loop subito senza attendere il click Start nel browser")
    parser.add_argument("--capturer",  choices=["auto", "wgc", "dxcam", "mss"], default="auto",
                        help="auto=WGC>dxcam>mss | wgc=Chrome-safe | dxcam=exclusive fullscreen | mss=GDI")
    args = parser.parse_args()

    _config["fps"]          = args.fps
    _config["strategy"]     = args.strategy
    _config["preview_only"] = args.preview
    _auto_switch            = (args.capturer == "auto")

    print("[Ambilight] POC avvio")
    settings = load_settings()
    host     = settings.get("openrgb_host", "localhost")
    port_rgb = settings.get("openrgb_port", 6742)

    dev_id, zones, total_leds = load_monitor_zones()
    _zones_list[:] = zones
    _total_leds    = total_leds
    _config["zones_enabled"] = {z["name"]: True for z in zones}

    _capturer_ref = make_capturer(args.fps, preferred=args.capturer)

    if not args.preview:
        print(f"[Ambilight] Connessione OpenRGB {host}:{port_rgb}...")
        try:
            _, device  = connect_openrgb(host, port_rgb, dev_id)
            _device_ref = device
        except Exception as exc:
            import traceback
            print(f"[Ambilight] OpenRGB non disponibile: {exc}")
            traceback.print_exc()
            print("[Ambilight] Preview forzato (nessun LED pilotato).")
            _config["preview_only"] = True
    else:
        print("[Ambilight] Modalita preview — nessun LED pilotato.")

    if args.autostart:
        _stop_event.clear()
        _capture_thread = threading.Thread(
            target=_capture_loop, daemon=True, name="ambilight-capture"
        )
        _capture_thread.start()

    web_dir = Path(__file__).parent / "web"
    eel.init(str(web_dir))
    print(f"\n[Ambilight] UI web su  http://localhost:{args.port}")
    print("            Apri l'URL nel browser, poi premi Start.\n")

    try:
        eel.start(
            "index.html",
            port           = args.port,
            mode           = None,
            block          = True,
            close_callback = _on_browser_close,
        )
    except KeyboardInterrupt:
        print("\n[Ambilight] Interruzione.")
    finally:
        _stop_event.set()
        if _capture_thread and _capture_thread.is_alive():
            _capture_thread.join(timeout=2.0)
        _capturer_ref.stop()
        print("[Ambilight] Uscita.")


if __name__ == "__main__":
    main()
