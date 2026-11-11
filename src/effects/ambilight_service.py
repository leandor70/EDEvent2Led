"""AmbilightService — idle background loop per ambilight.

Campiona lo schermo e invia i colori ai LED dei device configurati
quando nessun effetto visivo e' in corso.
"""

import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import numpy as np

from core.screen_capturer_service import ScreenCapturerService
from effects import topology_geometry as geo

CONFIG_PATH = Path("config/ambilight_config.json")

# Il lato dello schermo che un LED legge NON dipende dal nome della zona: lo
# decide dove il LED sta nella topologia rispetto al rettangolo schermo (vedi
# "Screen rectangle" sotto). Il nome e' solo un'etichetta scelta dall'utente.


# ── Sampling helpers ──────────────────────────────────────────────────────────


def _led_world_positions(zone: dict) -> List[Tuple[float, float]]:
    """Posizioni dei LED in coordinate-schermo: x a destra, y verso il BASSO.

    Le posizioni vengono da topology_geometry (la stessa geometria che disegna
    l'editor e che usano effetti e calibrazione: rotazione continua, direction,
    centro del LED), con y ribaltata perche' l'editor ha y verso l'alto mentre il
    frame catturato ha la riga 0 in cima. L'elemento i e' il LED i."""
    return [(x, -y) for x, y in geo.led_world_positions(zone)]


def _sample_segment(seg_2d: np.ndarray, strategy: str) -> Tuple[int, int, int]:
    pixels = seg_2d.reshape(-1, 3)
    if len(pixels) == 0:
        return (0, 0, 0)

    if strategy in ("percentile", "smooth", "adaptive", "adaptive_smooth"):
        # Mean of the brightest 20% of the pixels (exactly, by index: pixels tied
        # with the threshold do not count). It used to be the ONE pixel at the
        # 80th percentile: on dark content with colored text (a chat, an IDE) a
        # few changed pixels (a blinking cursor) moved that choice onto a pixel of
        # another color, and the LED jumped up to 225/255 between frames. The mean
        # moves in proportion (~7/255 for a cursor), still ignoring dark areas.
        lums = 0.2126 * pixels[:, 2] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 0]
        k    = int(len(lums) * 0.80)
        bgr  = pixels[np.argpartition(lums, k)[k:]].mean(axis=0)
    elif strategy == "dominant":
        bgr = np.median(pixels, axis=0)
    else:  # mean
        bgr = pixels.mean(axis=0)

    return (int(bgr[2]), int(bgr[1]), int(bgr[0]))


def _sample_area_point(
    frame: np.ndarray,
    x_pct: float,
    y_pct: float,
    strategy: str,
    radius_pct: float = 0.18,
) -> Tuple[int, int, int]:
    """Campiona la zona di schermo attorno a (x_pct, y_pct), entrambi in [0,1]
    con y_pct = 0 in CIMA allo schermo."""
    h, w = frame.shape[:2]
    cx = int(w * x_pct)
    cy = int(h * y_pct)
    r  = max(1, int(min(h, w) * radius_pct))
    x0, x1 = max(0, cx - r), min(w, cx + r)
    y0, y1 = max(0, cy - r), min(h, cy + r)
    patch = frame[y0:y1, x0:x1, :3].astype(np.float32)
    eff = "adaptive_smooth" if strategy in ("adaptive", "adaptive_smooth") else strategy
    return _sample_segment(patch, eff)


def _adaptive_depth(
    frame: np.ndarray,
    edge: str,
    screen_start: float,
    screen_end: float,
    min_pct: float,
    max_pct: float,
) -> float:
    h, w  = frame.shape[:2]
    probe = max(1, int(min(h, w) * 0.03))
    if edge in ("top", "bottom"):
        x0, x1 = int(w * screen_start), max(int(w * screen_start) + 1, int(w * screen_end))
        outer   = frame[:probe, x0:x1, :] if edge == "top" else frame[-probe:, x0:x1, :]
    else:
        y0, y1 = int(h * screen_start), max(int(h * screen_start) + 1, int(h * screen_end))
        outer   = frame[y0:y1, :probe, :] if edge == "left" else frame[y0:y1, -probe:, :]
    norm = min(1.0, float(outer.std()) / 80.0)
    return max_pct - norm * (max_pct - min_pct)


def _apply_temporal_smooth(
    prev_map: Dict[str, List[Tuple[int, int, int]]],
    zone_key: str,
    new_colors: List[Tuple[int, int, int]],
    alpha: float,
    cut_threshold: float,
) -> List[Tuple[int, int, int]]:
    prev = prev_map.get(zone_key)
    if prev is None or len(prev) != len(new_colors):
        prev_map[zone_key] = new_colors
        return new_colors

    avg_delta = sum(
        (abs(n[0] - p[0]) + abs(n[1] - p[1]) + abs(n[2] - p[2])) / 3
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

    prev_map[zone_key] = result
    return result


def _boost_saturation(
    colors: List[Tuple[int, int, int]],
    factor: float,
) -> List[Tuple[int, int, int]]:
    result = []
    for r, g, b in colors:
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        result.append((
            min(255, max(0, int(lum + (r - lum) * factor))),
            min(255, max(0, int(lum + (g - lum) * factor))),
            min(255, max(0, int(lum + (b - lum) * factor))),
        ))
    return result


def _sample_edge(
    frame: np.ndarray,
    edge: str,
    led_count: int,
    reversed_dir: bool,
    depth_pct: float,
    screen_start: float,
    screen_end: float,
    strategy: str,
    zone_key: str,
    prev_map: Dict,
    cfg: dict,
) -> List[Tuple[int, int, int]]:
    h, w = frame.shape[:2]

    if strategy in ("adaptive", "adaptive_smooth"):
        depth_pct = _adaptive_depth(
            frame, edge, screen_start, screen_end,
            min_pct=cfg.get("adaptive_min", 3.0) / 100.0,
            max_pct=cfg.get("adaptive_max", 20.0) / 100.0,
        )

    depth = max(1, int(min(h, w) * depth_pct))

    if edge in ("top", "bottom"):
        x0    = int(w * screen_start)
        x1    = max(x0 + 1, int(w * screen_end))
        strip = frame[:depth, x0:x1, :] if edge == "top" else frame[-depth:, x0:x1, :]
        axis  = 1
    else:
        y0    = int(h * screen_start)
        y1    = max(y0 + 1, int(h * screen_end))
        strip = frame[y0:y1, :depth, :] if edge == "left" else frame[y0:y1, -depth:, :]
        axis  = 0

    segs   = np.array_split(strip.astype(np.float32), led_count, axis=axis)
    colors = [_sample_segment(seg, strategy) for seg in segs]

    if strategy in ("smooth", "adaptive_smooth") and zone_key:
        colors = _apply_temporal_smooth(
            prev_map, zone_key, colors,
            alpha=cfg.get("ema_alpha", 0.35),
            cut_threshold=cfg.get("scene_cut", 60.0),
        )

    return colors[::-1] if reversed_dir else colors


# ── Zone discovery from topology ──────────────────────────────────────────────


def is_zone_enabled(zones_enabled: dict, zone: dict) -> bool:
    """Le zone si accendono/spengono per zone_index (i nomi possono ripetersi).

    Ripiego sulla chiave-nome scritta dalle versioni precedenti."""
    idx_key = str(zone.get("zone_index"))
    if idx_key in zones_enabled:
        return bool(zones_enabled[idx_key])
    return bool(zones_enabled.get(zone.get("name", ""), True))


# ── Screen rectangle (dove sta lo schermo nella scena della topologia) ────────
#
# Il lato dello schermo che un LED segue lo decide DOVE il LED e' disegnato,
# mai il nome della zona:
#   * LED su (o vicino a) un lato del rettangolo -> legge quel lato dello schermo
#   * LED dentro il rettangolo                   -> legge il punto di schermo sotto
#                                                    di lui (centro -> centro)
#   * LED fuori dal rettangolo                   -> non viene toccato
# "Vicino" = SCREEN_EDGE_BAND del lato corto, dentro o fuori, cosi' una striscia
# disegnata un po' sopra/sotto la cornice conta ancora come quel lato.
#
# Il rettangolo e' salvato in device_topologies.json come "screen_rect", in
# coordinate editor (y verso l'ALTO, come la posizione delle zone). Se manca si
# usa il riquadro che contiene i LED dei device accesi, portato alle proporzioni
# dello schermo reale.

SCREEN_EDGE_BAND = 0.15


def _valid_rect(r) -> bool:
    try:
        return (r["x_max"] - r["x_min"]) > 0 and (r["y_max"] - r["y_min"]) > 0
    except (KeyError, TypeError):
        return False


def _scene_points(data: dict, device_keys=None) -> List[Tuple[float, float]]:
    """Punti LED (coordinate-schermo, y GIU') dei device indicati (None = tutti)."""
    return [pt for key, topo in data.get("topologies", {}).items()
            if device_keys is None or key in device_keys
            for z in topo.get("zones", [])
            for pt in _led_world_positions(z)]


def fit_aspect(rect, aspect: Optional[float]):
    """Allarga (x_min, x_max, y_min, y_max) attorno al centro fino a larghezza/altezza = aspect.

    Solo allarga, mai restringe: cio' che il rettangolo inquadrava resta dentro
    (o nella fascia di bordo). aspect None / <= 0 lo lascia com'e'."""
    if not aspect or aspect <= 0:
        return rect
    x0, x1, y0, y1 = rect
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return rect
    if w / h < aspect:
        grow = (h * aspect - w) / 2
        return (x0 - grow, x1 + grow, y0, y1)
    grow = (w / aspect - h) / 2
    return (x0, x1, y0 - grow, y1 + grow)


def _bbox(pts) -> Tuple[float, float, float, float]:
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


def screen_frame(data: dict, device_keys=None, aspect: Optional[float] = None
                 ) -> Tuple[str, Tuple[float, float, float, float]]:
    """Come lo schermo e' collocato nella scena.

    Ritorna (mode, rect) con rect = (x_min, x_max, y_min, y_max) in coordinate di
    campionamento (y GIU', come _led_world_positions):
      "manual" -> lo screen_rect salvato
      "auto"   -> nessun rettangolo salvato: riquadro dei LED dei device indicati,
                  portato alle proporzioni dello schermo reale (aspect = w/h)
    """
    r = data.get("screen_rect")
    if _valid_rect(r):
        return "manual", (float(r["x_min"]), float(r["x_max"]), -float(r["y_max"]), -float(r["y_min"]))
    pts = _scene_points(data, device_keys)
    return "auto", fit_aspect(_bbox(pts) if pts else (0.0, 100.0, 0.0, 100.0), aspect)


def suggest_screen_rect(data: dict, device_keys=None, aspect: Optional[float] = None) -> Optional[dict]:
    """Rettangolo di partenza per l'editor (coordinate editor, y SU): il riquadro
    dei LED dei device indicati, alle proporzioni dello schermo."""
    pts = _scene_points(data, device_keys)
    if not pts:
        return None
    x0, x1, y0, y1 = _bbox(pts)
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return None
    x0, x1, y0, y1 = fit_aspect((x0, x1, y0, y1), aspect)
    return {"x_min": x0, "x_max": x1, "y_min": -y1, "y_max": -y0}


def _classify_led(x: float, y: float, rect, band: float, along_axis: Optional[str] = None,
                  reach: float = 0.5):
    """("off",) | ("edge", side, along 0..1) | ("area", x_pct, y_pct).

    Un LED appartiene a un lato se sta entro `band` da esso TRASVERSALMENTE (una
    striscia un po' sopra/sotto la cornice conta) e dentro la lunghezza del lato
    LUNGO di esso, piu' o meno `reach` (mezzo LED): oltre l'angolo e' fuori.
    along_axis ("x" o "y") e' la direzione della striscia: segue solo i lati
    paralleli (una striscia orizzontale non legge mai il lato sinistro/destro,
    nemmeno vicino a un angolo)."""
    x0, x1, y0, y1 = rect
    w, h = max(0.001, x1 - x0), max(0.001, y1 - y0)
    d = {"left": x - x0, "right": x1 - x, "top": y - y0, "bottom": y1 - y}
    in_x = x0 - reach <= x <= x1 + reach
    in_y = y0 - reach <= y <= y1 + reach
    near = [k for k in d if abs(d[k]) <= band and (in_x if k in ("top", "bottom") else in_y)]
    if along_axis:
        near = [k for k in near if (k in ("top", "bottom")) == (along_axis == "x")]
    if near:
        side = min(near, key=lambda k: abs(d[k]))
        along = (x - x0) / w if side in ("top", "bottom") else (y - y0) / h
        return ("edge", side, max(0.0, min(1.0, along)))
    if x0 <= x <= x1 and y0 <= y <= y1:
        return ("area", (x - x0) / w, (y - y0) / h)
    return ("off",)


def _geometric_entries(zone: dict, led_offset: int, rect) -> List[dict]:
    """Voci di campionamento di una zona, LED per LED, da dove stanno i suoi LED.

    LED consecutivi sullo stesso lato diventano una voce "edge" (una zona che
    supera un angolo cede i LED d'angolo al lato con cui e' parallela); i LED
    dentro diventano una voce "area" ciascuno; quelli fuori una voce "off"
    (elencata, mai campionata)."""
    pts = _led_world_positions(zone)
    if not pts:
        return []
    x0, x1, y0, y1 = rect
    w, h = max(0.001, x1 - x0), max(0.001, y1 - y0)
    band = max(1.0, SCREEN_EDGE_BAND * min(w, h))
    spacing = zone.get("led_spacing", 1.0)
    base = {"name": zone.get("name", ""), "zone_index": zone["zone_index"],
            "led_count": zone["led_count"], "led_offset": led_offset,
            "screen_start": 0.0, "screen_end": 1.0, "reversed": False}

    axis = None
    if len(pts) > 1:
        axis = "x" if abs(pts[-1][0] - pts[0][0]) >= abs(pts[-1][1] - pts[0][1]) else "y"
    reach = max(0.5, spacing / 2)
    kinds = [_classify_led(x, y, rect, band, axis, reach) for x, y in pts]
    out: List[dict] = []
    i = 0
    while i < len(kinds):
        k = kinds[i]
        j = i + 1
        if k[0] in ("edge", "off"):
            while j < len(kinds) and kinds[j][0] == k[0] and kinds[j][1:2] == k[1:2]:
                j += 1
        if k[0] == "off":
            out.append({**base, "edge": "off", "led_start": i, "led_end": j})
        elif k[0] == "area":
            out.append({**base, "edge": "area", "led_start": i, "led_end": i + 1,
                        "x_pct": k[1], "y_pct": k[2]})
        else:
            side = k[1]
            along = [kinds[n][2] for n in range(i, j)]
            span = w if side in ("top", "bottom") else h
            half = spacing / 2 / span
            out.append({**base, "edge": side, "led_start": i, "led_end": j,
                        "screen_start": max(0.0, min(along) - half),
                        "screen_end":   min(1.0, max(along) + half),
                        "reversed":     len(along) > 1 and along[0] > along[-1]})
        i = j
    return out


def summarize_zones(entries: List[dict]) -> List[dict]:
    """Una voce per zona (le voci di una zona condividono zone_index), per elenchi e conteggi.

    edge: "top", "area", varie unite da "+" ("top+right"), oppure "off" se ogni
    LED della zona e' fuori dallo schermo (non viene mai pilotata)."""
    by_idx: Dict[int, dict] = {}
    for e in entries:
        s = by_idx.setdefault(e["zone_index"], {
            "zone_index": e["zone_index"], "name": e["name"], "_kinds": []})
        if e["edge"] != "off" and e["edge"] not in s["_kinds"]:
            s["_kinds"].append(e["edge"])
    out = []
    for s in by_idx.values():
        kinds = s.pop("_kinds")
        s["edge"] = "+".join(kinds) if kinds else "off"
        s["outside"] = not kinds
        out.append(s)
    return out


def build_device_zones(device_key: str, aspect: Optional[float] = None,
                       scene_keys=None) -> Tuple[List[dict], int]:
    """Carica da device_topologies.json i parametri di campionamento di un device.

    Ritorna (voci, led_totali). Le voci di una zona possono essere piu' d'una
    (una per lato / punto / tratto fuori schermo): condividono zone_index e si
    distinguono per led_start..led_end. Chiavi: name, zone_index, led_count,
    led_offset, led_start, led_end, screen_start, screen_end, edge, reversed
    (e x_pct/y_pct per edge == "area").

    `scene_keys`: device che definiscono il riquadro automatico (None = tutti)."""
    try:
        data = json.loads(Path("config/device_topologies.json").read_text(encoding="utf-8"))
    except Exception:
        return [], 0

    topology = data.get("topologies", {}).get(device_key)
    if not topology:
        return [], 0

    saved_zones = topology.get("zones", [])
    indexes     = [z["zone_index"] for z in saved_zones]
    if len(indexes) != len(set(indexes)):
        # JSON salvato da versioni vecchie con segmenti: il contatore ripartiva
        # da 0 per ogni zona. L'ordine nel file e' quello hardware (lo usa anche
        # Linear1D): rinumera per posizione, altrimenti sorted() lo rimescola.
        saved_zones = [{**z, "zone_index": i} for i, z in enumerate(saved_zones)]
    all_zones = sorted(saved_zones, key=lambda z: z["zone_index"])
    if not all_zones:
        return [], 0

    # Offset dei LED per posizione, non per zone_index: con indici ripetuti una
    # mappa per indice sovrascriverebbe le zone.
    zone_offsets: List[int] = []
    off = 0
    for zone in all_zones:
        zone_offsets.append(off)
        off += zone["led_count"]
    total_leds = off

    _, rect = screen_frame(data, scene_keys, aspect)
    result: List[dict] = []
    for z_idx, zone in enumerate(all_zones):
        result.extend(_geometric_entries(zone, zone_offsets[z_idx], rect))
    return result, total_leds


# ── Service ───────────────────────────────────────────────────────────────────


class AmbilightService:
    """
    Servizio ambilight idle: quando nessun effetto e' in corso, campiona
    lo schermo e invia i colori ai device configurati.
    """

    def __init__(self, effect_manager) -> None:
        self._effect_manager = effect_manager
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._config: dict = self._load_config()
        self._prev_colors: Dict[str, List[Tuple[int, int, int]]] = {}
        self._actual_fps: float = 0.0
        self._paused: bool = False  # Temporary hold (e.g. during topology calibration)
        # Serializza scrittura dei frame e blackout di pause(): senza, un frame gia'
        # campionato puo' finire sui LED subito dopo il blackout.
        self._write_lock = threading.Lock()
        # Zone cache: device_key -> (zones, total_leds) — invalidated on topology save
        self._zone_cache: Dict[str, Tuple[List[dict], int]] = {}
        self._topology_warned: set = set()
        # Dimensioni dell'ultimo frame catturato (w, h): servono al riquadro schermo
        # automatico, che prende le proporzioni dello schermo reale.
        self._frame_size: Optional[Tuple[int, int]] = None
        # device_key -> indici dei LED scritti all'ultimo frame. Un LED che esce
        # dall'uso (zona spenta, rettangolo spostato) riceve il nero una volta sola;
        # gli altri LED del device non vengono mai toccati.
        self._led_in_use: Dict[str, set] = {}

    def set_effect_manager(self, effect_manager) -> None:
        """Point the service at another effect manager (OpenRGB reconnection,
        "Test connection"). None = sample but do not write.

        Without this the service kept the manager it was created with: it asked
        THAT manager whether an effect was playing (always no, effects now run on
        the new one) and wrote over the effects."""
        with self._write_lock:
            self._effect_manager = effect_manager
            self._led_in_use.clear()
            self._zone_cache.clear()

    # ── Config ────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_config() -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {
                "version": 1, "enabled": False, "capturer": "auto",
                "fps": 15, "strategy": "adaptive_smooth",
                "depth": 10, "saturation_boost": 1.4,
                "ema_alpha": 0.35, "scene_cut": 60,
                "adaptive_min": 3, "adaptive_max": 20, "devices": {},
            }

    @staticmethod
    def _save_config(cfg: dict) -> None:
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get_config(self) -> dict:
        return dict(self._config)

    def set_config(self, updates: dict) -> None:
        if "strategy" in updates and updates["strategy"] != self._config.get("strategy"):
            self._prev_colors.clear()
        self._config.update(updates)
        self._save_config(self._config)
        if "devices" in updates:
            # I device accesi definiscono il riquadro schermo automatico
            self.refresh_all_zones()
        svc = ScreenCapturerService.get_instance()
        if "fps" in updates and svc.is_running:
            svc.set_fps(int(updates["fps"]))

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def actual_fps(self) -> float:
        return self._actual_fps

    @property
    def capturer_name(self) -> str:
        return ScreenCapturerService.get_instance().capturer_name

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Avvia il loop idle. Idempotente."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._idle_loop, daemon=True, name="ambilight-idle"
        )
        self._thread.start()
        print("[Ambilight] Service started")

    def stop(self) -> None:
        """Ferma il loop e il capturer."""
        self._stop_event.set()
        ScreenCapturerService.get_instance().stop()

    def pause(self) -> None:
        """Sospende l'output Ambilight senza fermare il capturer e spegne i LED gestiti.

        Usato da calibrazione topologia e flash di identificazione: devono
        possedere i LED. Oltre a smettere di campionare, si spegne ogni device
        pilotato dall'ambilight, altrimenti quelli non coperti dalla calibrazione
        (o i LED fuori topologia) restano congelati sull'ultimo frame."""
        # Blackout solo alla transizione: la calibrazione richiama pause() a ogni
        # modifica di centro/spaziatura, a thread gia' attivo -> niente sfarfallio.
        with self._write_lock:
            already_paused = self._paused
            self._paused = True
            if not already_paused:
                self._blackout()

    def resume(self) -> None:
        """Riprende l'output Ambilight dopo una pausa."""
        self._paused = False

    def simulate_idle(self) -> dict:
        """Riporta l'ambilight nello stato idle, per provarlo senza aspettare.

        L'ambilight scrive sui LED solo quando nessun effetto e' in corso e non
        e' in pausa: qui si ferma ogni effetto attivo (il che rilascia anche il
        lock tastiera), si toglie l'eventuale pausa e ci si assicura che il loop
        giri. Ritorna lo stato che serve a spiegare all'utente perche' i LED
        potrebbero non cambiare (servizio disabilitato, nessun device attivo)."""
        if self._effect_manager:
            self._effect_manager.stop_all_effects()
        self.resume()
        self.start()
        devices = self._config.get("devices", {})
        return {
            "ok": True,
            "enabled": bool(self._config.get("enabled", False)),
            "running": self.is_running,
            "active_devices": sum(1 for d in devices.values() if d.get("enabled", False)),
        }

    def is_device_enabled(self, device_key: str) -> bool:
        """True se il device e' pilotato dall'ambilight (enabled in ambilight_config)."""
        return bool(self._config.get("devices", {}).get(device_key, {}).get("enabled", False))

    def _blackout(self) -> None:
        """Invia nero ai device abilitati. Chiamare con _write_lock acquisito."""
        if not self._effect_manager:
            return
        for device_ctrl in self._effect_manager.devices:
            device_key = self._effect_manager._make_device_key(device_ctrl)
            if not self.is_device_enabled(device_key):
                continue
            # Conteggio dall'hardware: la topologia salvata puo' essere disallineata
            led_count = device_ctrl.topology.led_count
            if led_count > 0:
                self._effect_manager.apply_direct_colors(device_key, [(0, 0, 0)] * led_count)

    # ── Zone cache ────────────────────────────────────────────────────────────

    def refresh_all_zones(self) -> None:
        """Invalida la cache zone di tutti i device (dopo una scrittura di device_topologies.json)."""
        self._zone_cache.clear()
        self._topology_warned.clear()

    def refresh_zones(self, device_key: str) -> None:
        """Invalida la cache zone per un device (da chiamare dopo salvataggio topologia)."""
        self._zone_cache.pop(device_key, None)
        self._topology_warned.discard(device_key)

    @property
    def frame_size(self) -> Optional[Tuple[int, int]]:
        """(larghezza, altezza) dell'ultimo frame catturato, None se non ce n'e' ancora."""
        return self._frame_size

    def _scene_keys(self):
        """Device che definiscono il riquadro schermo automatico: quelli accesi
        nell'ambilight (None = tutti, se nessuno e' acceso)."""
        keys = {k for k, d in self._config.get("devices", {}).items() if d.get("enabled", False)}
        return keys or None

    def get_device_zones(self, device_key: str) -> Tuple[List[dict], int]:
        if device_key not in self._zone_cache:
            size = self._frame_size
            aspect = (size[0] / size[1]) if size and size[1] else None
            zones, total_leds = build_device_zones(device_key, aspect, self._scene_keys())
            self._validate_topology(device_key, total_leds)
            self._zone_cache[device_key] = (zones, total_leds)
        return self._zone_cache[device_key]

    def _validate_topology(self, device_key: str, total_leds: int) -> None:
        """Avvisa (una volta per device) se i LED della topologia non coincidono
        con quelli dell'hardware. Il sync all'avvio di topology_api li riallinea;
        se resta una differenza (sync fallito, device fuori dal sync) l'ambilight
        non riesce a scrivere su quel device, e l'avviso dice dove guardare."""
        if not self._effect_manager or total_leds <= 0 or device_key in self._topology_warned:
            return
        for device_ctrl in self._effect_manager.devices:
            if self._effect_manager._make_device_key(device_ctrl) != device_key:
                continue
            hw_led_count = device_ctrl.topology.led_count
            if hw_led_count != total_leds:
                self._topology_warned.add(device_key)
                print(f"[Ambilight] Topology mismatch for '{device_key}': config declares "
                      f"{total_leds} LEDs but hardware reports {hw_led_count}. "
                      f"The ambilight cannot drive this device until the zones are "
                      f"reloaded from the Topology Editor.")
            return

    # ── Idle loop ─────────────────────────────────────────────────────────────

    def _idle_loop(self) -> None:
        svc = ScreenCapturerService.get_instance()

        try:
            import ctypes as _ct
            _ct.windll.winmm.timeBeginPeriod(1)
            _timer_ok = True
        except Exception:
            _timer_ok = False

        try:
            while not self._stop_event.is_set():
                t0  = time.perf_counter()
                cfg = dict(self._config)

                if not cfg.get("enabled", False):
                    # Stop capturer to save GPU/CPU when idle is disabled
                    if svc.is_running:
                        svc.stop()
                    self._stop_event.wait(0.5)
                    continue

                # Start capturer lazily on first enabled frame
                if not svc.is_running:
                    svc.start(
                        fps=int(cfg.get("fps", 15)),
                        preferred=cfg.get("capturer", "auto"),
                    )
                    self._stop_event.wait(0.1)
                    continue

                # Yield to active effects — ambilight must not overwrite animations
                if self._effect_manager and self._effect_manager.is_effect_playing():
                    self._stop_event.wait(0.1)
                    continue

                # Yield while explicitly paused (e.g. topology calibration is running)
                if self._paused:
                    self._stop_event.wait(0.1)
                    continue

                frame = svc.get_latest_frame()
                if frame is None:
                    self._stop_event.wait(0.02)
                    continue

                self._process_frame(frame, cfg)

                elapsed = time.perf_counter() - t0
                if elapsed > 0:
                    self._actual_fps = round(0.85 * self._actual_fps + 0.15 / elapsed, 1)

                wait = 1.0 / max(1, int(cfg.get("fps", 15))) - elapsed
                if wait > 0:
                    self._stop_event.wait(wait)
        finally:
            if _timer_ok:
                import ctypes as _ct
                _ct.windll.winmm.timeEndPeriod(1)

    def _process_frame(self, frame: np.ndarray, cfg: dict) -> None:
        """Campiona il frame e invia i colori ai device configurati."""
        full_h, full_w = frame.shape[:2]
        if self._frame_size != (full_w, full_h):
            # Nuovo schermo / risoluzione: il riquadro automatico cambia proporzioni
            self._frame_size = (full_w, full_h)
            self._zone_cache.clear()

        strategy    = cfg.get("strategy", "adaptive_smooth")
        depth_pct   = cfg.get("depth", 10.0) / 100.0
        sat_boost   = cfg.get("saturation_boost", 1.4)
        devices_cfg = cfg.get("devices", {})
        smoothing   = strategy in ("smooth", "adaptive_smooth")

        for device_key, dev_cfg in devices_cfg.items():
            if not dev_cfg.get("enabled", False):
                continue

            zones, total_leds = self.get_device_zones(device_key)
            if not zones or total_leds == 0:
                continue

            zones_enabled = dev_cfg.get("zones_enabled", {})
            led_colors: Dict[int, Tuple[int, int, int]] = {}

            for zone in zones:
                if zone["edge"] == "off" or not is_zone_enabled(zones_enabled, zone):
                    continue

                led_start = zone["led_start"]
                active    = zone["led_end"] - led_start
                off       = zone["led_offset"] + led_start
                zone_key  = f"{device_key}:{zone['zone_index']}:{led_start}"

                if zone["edge"] == "area":
                    zone_colors = [_sample_area_point(
                        frame, zone["x_pct"], zone["y_pct"], strategy)]
                    if smoothing:
                        zone_colors = _apply_temporal_smooth(
                            self._prev_colors, zone_key, zone_colors,
                            alpha=cfg.get("ema_alpha", 0.35),
                            cut_threshold=cfg.get("scene_cut", 60.0),
                        )
                else:
                    zone_colors = _sample_edge(
                        frame,
                        edge         = zone["edge"],
                        led_count    = active,
                        reversed_dir = zone["reversed"],
                        depth_pct    = depth_pct,
                        screen_start = zone["screen_start"],
                        screen_end   = zone["screen_end"],
                        strategy     = strategy,
                        zone_key     = zone_key,
                        prev_map     = self._prev_colors,
                        cfg          = cfg,
                    )

                zone_colors = _boost_saturation(zone_colors, sat_boost)
                for k, color in enumerate(zone_colors):
                    led_colors[off + k] = color

            if not self._effect_manager:
                continue

            # Salta la scrittura se una pausa e' arrivata a meta' frame (es. e' appena
            # partita la calibrazione): evita un frame ambilight che la contrasta.
            with self._write_lock:
                if self._paused:
                    continue
                # Solo i LED in uso: gli altri restano a chi li usa (effetti, OpenRGB).
                # Un LED che smette di essere usato riceve il nero una volta sola.
                in_use = set(led_colors)
                for idx in self._led_in_use.get(device_key, set()) - in_use:
                    led_colors[idx] = (0, 0, 0)
                self._led_in_use[device_key] = in_use
                if led_colors:
                    self._effect_manager.apply_direct_leds(device_key, led_colors)
