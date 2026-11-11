"""
topology_geometry.py — Geometria delle zone della topologia (UNICA fonte).

La topologia (config/device_topologies.json) e' il modo in cui l'utente spiega
al motore dove sono i LED e come sono costruiti: posizione, rotazione, passo,
verso. Questo modulo traduce quei dati in coordinate, ed e' usato da TUTTI:
effetti spaziali (Linear1D), calibrazione ad anelli e ambilight. Nessuno deve
ricalcolare le posizioni per conto suo.

Gemello 1:1 di web/js/topology-editor.js:

  led_world_position  <-> _ledWorldPos()        (centro del LED disegnato)
  zone_corners        <-> getZoneCorners()      (rettangolo 0..w x -1..0 ruotato)
  scene_bbox          <-> calculateBoundingBox() (min/max sui corner)

Convenzione world (y verso l'ALTO, come l'editor):
    world = position + R(rot) . local      con local = (lx, ly)
    R(a) = [[cos a, -sin a], [sin a, cos a]]

La zona e' il rettangolo locale 0..w x -1..0 (w = led_count * led_spacing): il
LED di slot k occupa x in [k*spacing, (k+1)*spacing], quindi il suo centro e'
((k+0.5)*spacing, -0.5). La rotazione e' continua (qualsiasi angolo).

`direction` ("forward" | "reverse"): con "reverse" la zona e' cablata al
contrario, cioe' il LED 0 sta all'estremo lontano. Il LED i occupa lo slot
led_count-1-i. L'ordine hardware dei LED non cambia: cambia dove stanno.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple


def led_slot(zone: dict, led_index: int) -> int:
    """Slot (0 = estremo di ancoraggio della zona) in cui sta il LED `led_index`."""
    if zone.get("direction") == "reverse":
        return int(zone["led_count"]) - 1 - led_index
    return led_index


def led_world_position(zone: dict, led_index: int) -> Tuple[float, float]:
    """
    World position del CENTRO del LED `led_index` (y verso l'alto).
    Gemello di _ledWorldPos() dell'editor.
    """
    spacing = float(zone.get("led_spacing", 1.0))
    lx = (led_slot(zone, led_index) + 0.5) * spacing
    ly = -0.5
    rad = math.radians(zone.get("rotation", 0) or 0)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    x0 = zone["position"]["x"]
    y0 = zone["position"]["y"]
    return (
        x0 + lx * cos_r - ly * sin_r,
        y0 + lx * sin_r + ly * cos_r,
    )


def led_world_positions(zone: dict) -> List[Tuple[float, float]]:
    """Centri di tutti i LED della zona, nell'ordine hardware (item i = LED i)."""
    return [led_world_position(zone, i) for i in range(int(zone["led_count"]))]


def zone_corners(zone: dict) -> List[Tuple[float, float]]:
    """
    I 4 corner (world) del rettangolo zona 0..w x -1..0, ruotati di `rotation`.
    Gemello di getZoneCorners(). w = led_count * led_spacing.
    """
    w = zone["led_count"] * float(zone.get("led_spacing", 1.0))
    rad = math.radians(zone.get("rotation", 0) or 0)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    x0 = zone["position"]["x"]
    y0 = zone["position"]["y"]
    local = ((0.0, -1.0), (w, -1.0), (w, 0.0), (0.0, 0.0))
    return [
        (x0 + cx * cos_r - cy * sin_r, y0 + cx * sin_r + cy * cos_r)
        for cx, cy in local
    ]


def scene_bbox(zones: Sequence[dict]) -> Tuple[float, float, float, float]:
    """
    Bounding box (min_x, max_x, min_y, max_y) sui corner di TUTTE le zone.
    Gemello di calculateBoundingBox(). Ritorna (0,0,0,0) se non ci sono zone.
    """
    pts = [p for z in zones for p in zone_corners(z)]
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), max(xs), min(ys), max(ys))
