"""
Ambilight API — Eel endpoints per la configurazione e il controllo ambilight.

Fonte di verita' per lo stato enabled di un device:
  - ambilight_config.json  devices[key].enabled  (letta dal servizio a runtime)
  - device_config.json     devices[key].on_disable == "ambilight"  (letta da devices.html)

Le due fonti vengono mantenute in sync da questo modulo: ogni scrittura via
set_ambilight_device_enabled() aggiorna ENTRAMBI i file.
Al caricamento (get_ambilight_devices) viene eseguita una riconciliazione
per gestire il caso di avvio dopo editing manuale o crash.
"""

import eel
import json
from pathlib import Path
from typing import Optional

from utils.device_keys import display_name

_ambilight_service: Optional[object] = None
_effect_manager:    Optional[object] = None

_DEVICE_CONFIG_PATH = Path("config/device_config.json")


def init_ambilight_api(ambilight_service, effect_manager) -> None:
    global _ambilight_service, _effect_manager
    _ambilight_service = ambilight_service
    _effect_manager    = effect_manager
    print("[OK] Ambilight API initialized")


def set_effect_manager(manager) -> None:
    """Update the effect manager after an OpenRGB (re)connection: the API and the
    service must follow the manager that plays the effects."""
    global _effect_manager
    _effect_manager = manager
    if _ambilight_service is not None:
        _ambilight_service.set_effect_manager(manager)


# ── Helpers device_config.json ────────────────────────────────────────────────


def _read_device_config() -> dict:
    try:
        return json.loads(_DEVICE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "devices": {}}


def _write_device_config(cfg: dict) -> None:
    try:
        _DEVICE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DEVICE_CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        print(f"[ambilight_api] Could not write device_config: {exc}")


def _sync_device_config(device_key: str, enabled: bool) -> None:
    """
    Aggiorna device_config.json in modo coerente con lo stato ambilight:
      enabled=True  → on_disable = "ambilight"
      enabled=False → on_disable = "keep"  (solo se era "ambilight")
    """
    dev_cfg = _read_device_config()
    devices = dev_cfg.setdefault("devices", {})
    if device_key not in devices:
        devices[device_key] = {"enabled": True}
    entry = devices[device_key]
    if enabled:
        entry["on_disable"] = "ambilight"
    elif entry.get("on_disable") == "ambilight":
        entry["on_disable"] = "keep"
    _write_device_config(dev_cfg)


# ── Config ────────────────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_config() -> dict:
    if _ambilight_service is None:
        return {}
    return _ambilight_service.get_config()


@eel.expose
def set_ambilight_config(updates: dict) -> dict:
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    try:
        _ambilight_service.set_config(updates)
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Status ────────────────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_status() -> dict:
    if _ambilight_service is None:
        return {"running": False, "fps": 0.0, "capturer": "—", "enabled": False}
    cfg = _ambilight_service.get_config()
    return {
        "running":  _ambilight_service.is_running,
        "fps":      _ambilight_service.actual_fps,
        "capturer": _ambilight_service.capturer_name,
        "enabled":  cfg.get("enabled", False),
    }


@eel.expose
def test_ambilight_idle() -> dict:
    """Forza lo stato idle: ferma gli effetti in corso e lascia i LED all'ambilight."""
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    try:
        return _ambilight_service.simulate_idle()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Device enumeration ────────────────────────────────────────────────────────


@eel.expose
def get_ambilight_devices() -> list:
    """
    Ritorna la lista dei device disponibili per ambilight (no MATRIX/keyboard).

    Esegue una riconciliazione tra ambilight_config e device_config:
    se un device ha on_disable='ambilight' in device_config ma enabled=False
    in ambilight_config (es. dopo un riavvio), lo riabilita in ambilight_config.
    """
    if _effect_manager is None:
        return []

    from effects.device_topology import TopologyType
    ambi_cfg         = _ambilight_service.get_config() if _ambilight_service else {}
    ambi_devices     = dict(ambi_cfg.get("devices", {}))
    dev_cfg_devices  = _read_device_config().get("devices", {})

    ambi_cfg_dirty   = False
    result           = []

    for device_ctrl in _effect_manager.devices:
        # Keyboards are excluded by the type OpenRGB reports: one without a
        # matrix map falls back to LINEAR and would otherwise be offered here.
        raw_type = getattr(getattr(device_ctrl.topology.device, "type", None), "name", "")
        if device_ctrl.topology.topology_type == TopologyType.MATRIX or raw_type == "KEYBOARD":
            continue

        device_key = _effect_manager._make_device_key(device_ctrl)
        zones      = _device_zone_summary(device_key)
        ambi_entry = ambi_devices.get(device_key, {})
        dc_entry   = dev_cfg_devices.get(device_key, {})

        # Riconciliazione startup: device_config dice "ambilight" ma ambilight_config dice disabled
        if dc_entry.get("on_disable") == "ambilight" and not ambi_entry.get("enabled", False):
            ambi_devices.setdefault(device_key, {})["enabled"] = True
            ambi_cfg_dirty = True

        enabled = ambi_devices.get(device_key, {}).get("enabled", False)

        result.append({
            "device_key":    device_key,
            "name":          display_name(device_ctrl, _effect_manager.devices),
            "led_count":     device_ctrl.topology.led_count,
            "topology_type": device_ctrl.topology.topology_type.name.lower(),
            # has_topology = il device ha zone nella topologia (si puo' accendere);
            # on_screen = almeno una zona cade sul rettangolo schermo. Tenerli
            # separati: un device spento puo' stare fuori dal riquadro automatico
            # (che conta solo i device accesi) e deve comunque poter essere acceso.
            "has_topology":  bool(zones),
            "on_screen":     any(not z["outside"] for z in zones),
            "zone_count":    len(zones),
            "enabled":       enabled,
        })

    # Persiste la riconciliazione se necessario
    if ambi_cfg_dirty and _ambilight_service:
        _ambilight_service.set_config({"devices": ambi_devices})

    return result


@eel.expose
def set_ambilight_device_enabled(device_key: str, enabled: bool) -> dict:
    """
    Abilita/disabilita un device per ambilight.

    Aggiorna ENTRAMBI i file di configurazione in modo atomico:
      ambilight_config.json  → devices[key].enabled
      device_config.json     → devices[key].on_disable ("ambilight" | "keep")
    """
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    try:
        # 1. Aggiorna ambilight_config.json (fonte di verita' per il servizio)
        cfg     = _ambilight_service.get_config()
        devices = cfg.get("devices", {})
        if device_key not in devices:
            devices[device_key] = {}
        devices[device_key]["enabled"] = enabled
        _ambilight_service.set_config({"devices": devices})

        # 2. Sincronizza device_config.json (fonte di verita' per devices.html)
        _sync_device_config(device_key, enabled)

        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _device_zone_summary(device_key: str) -> list:
    """Zone di un device riassunte (una per zone_index): lato/i, se e' fuori schermo.

    Passa dal servizio, cosi' usa le stesse proporzioni dello schermo e lo stesso
    riquadro dei device accesi che usa il campionamento."""
    from effects.ambilight_service import build_device_zones, summarize_zones
    if _ambilight_service is not None:
        entries, _ = _ambilight_service.get_device_zones(device_key)
    else:
        entries, _ = build_device_zones(device_key)
    return summarize_zones(entries)


@eel.expose
def set_ambilight_zone_enabled(device_key: str, zone_index, enabled: bool) -> dict:
    """Accende/spegne una zona. zone_index e' l'indice della zona (un nome, da
    chiamanti vecchi, viene accettato come chiave legacy)."""
    if _ambilight_service is None:
        return {"ok": False, "error": "Service not initialized"}
    cfg     = _ambilight_service.get_config()
    devices = cfg.get("devices", {})
    if device_key not in devices:
        devices[device_key] = {}
    dev_entry = devices[device_key]
    if "zones_enabled" not in dev_entry:
        dev_entry["zones_enabled"] = {}
    dev_entry["zones_enabled"][str(zone_index)] = enabled
    _ambilight_service.set_config({"devices": devices})
    return {"ok": True}


@eel.expose
def get_ambilight_device_zones(device_key: str) -> list:
    """Zone di un device: {zone_index, name, edge, outside, enabled}.

    edge e' dedotto dalla posizione dei LED rispetto al rettangolo schermo
    ("top", "left+bottom", "area"...), "off" se la zona e' tutta fuori."""
    from effects.ambilight_service import is_zone_enabled
    zones_ena = {}
    if _ambilight_service is not None:
        zones_ena = _ambilight_service.get_config().get("devices", {}).get(
            device_key, {}).get("zones_enabled", {})
    return [{
        "zone_index": z["zone_index"],
        "name":       z["name"],
        "edge":       z["edge"],
        "outside":    z["outside"],
        "enabled":    is_zone_enabled(zones_ena, z),
    } for z in _device_zone_summary(device_key)]
