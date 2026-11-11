"""
Status.json Monitor - Real-time game state monitoring

This module monitors the Elite Dangerous Status.json file for flag changes
and triggers RGB effects based on game state (overheating, interdiction, etc.)

Author: EDLogReader Project
"""

import json
import time
from pathlib import Path
from typing import Dict, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class StatusMonitor:
    """
    Monitors Status.json for flag changes and triggers RGB effects

    The Status.json file is updated by Elite Dangerous every ~0.5-1 seconds
    with the current game state. This monitor watches for flag changes and
    triggers appropriate RGB effects for critical states like overheating,
    interdiction, low fuel, etc.
    """

    # All 32 bits of the Flags field — complete coverage
    MONITORED_FLAGS = {
        # ── Pericolo immediato (priority 9-10) ───────────────────────────────
        30: {"name": "FSDJump",           "effect": "hyperspace_jump",    "priority": 10},
        20: {"name": "Overheating",       "effect": "overheat_warning",   "priority": 10},
        22: {"name": "BeingInterdicted",  "effect": "interdiction_alert", "priority": 10},
        23: {"name": "InDanger",          "effect": "danger_alert",       "priority": 9},
        19: {"name": "LowFuel",           "effect": "low_fuel_warning",   "priority": 8},

        # ── FSD state machine (priority 6-7) ─────────────────────────────────
        17: {"name": "FsdCharging",       "effect": "fsd_charging",       "priority": 7},
        16: {"name": "MassLocked",        "effect": "mass_locked",        "priority": 6},
        18: {"name": "FsdCooldown",       "effect": "fsd_cooldown",       "priority": 3},

        # ── Combattimento (priority 5-6) ─────────────────────────────────────
        6:  {"name": "HardpointsDeployed","effect": "combat_ready",       "priority": 6},

        # ── Stato speciale (priority 3-5) ────────────────────────────────────
        10: {"name": "SilentRunning",     "effect": "stealth_mode",       "priority": 5},
        11: {"name": "ScoopingFuel",      "effect": "fuel_scooping",      "priority": 5},
        9:  {"name": "CargoScoopDeployed","effect": "cargo_scoop",        "priority": 4},
        5:  {"name": "FlightAssistOff",   "effect": "flight_assist_off",  "priority": 4},

        # ── Navigazione / assetto (priority 2-4) ─────────────────────────────
        4:  {"name": "Supercruise",       "effect": "supercruise_active", "priority": 4},
        0:  {"name": "Docked",            "effect": "docked_safe",        "priority": 4},
        1:  {"name": "Landed",            "effect": "landed_planet",      "priority": 3},
        2:  {"name": "LandingGearDown",   "effect": "landing_gear",       "priority": 3},

        # ── Stato nave (priority 1-2) ─────────────────────────────────────────
        3:  {"name": "ShieldsUp",         "effect": "shields_active",     "priority": 2},
        7:  {"name": "InWing",            "effect": "in_wing",            "priority": 2},
        8:  {"name": "LightsOn",          "effect": "lights_on",          "priority": 1},
        28: {"name": "NightVision",       "effect": "night_vision_mode",  "priority": 2},
        27: {"name": "HudAnalysisMode",   "effect": "analysis_mode",      "priority": 2},

        # ── Veicolo attivo — mutuamente esclusivi ────────────────────────────
        24: {"name": "InMainShip",        "effect": "in_main_ship",       "priority": 2},
        25: {"name": "InFighter",         "effect": "in_fighter",         "priority": 2},
        26: {"name": "InSRV",             "effect": "in_srv",             "priority": 2},

        # ── SRV-specific ──────────────────────────────────────────────────────
        12: {"name": "SrvHandBrake",      "effect": "srv_handbrake",      "priority": 3},
        13: {"name": "SrvTurretView",     "effect": "srv_turret_view",    "priority": 3},
        14: {"name": "SrvTurretRetracted","effect": "srv_turret_near",    "priority": 2},
        15: {"name": "SrvDriveAssist",    "effect": "srv_drive_assist",   "priority": 2},
        31: {"name": "SrvHighBeam",       "effect": "srv_high_beam",      "priority": 1},

        # ── Informazionali (priority 1) ───────────────────────────────────────
        21: {"name": "HasLatLong",        "effect": "has_lat_long",       "priority": 1},
        29: {"name": "AltFromAvgRadius",  "effect": "near_surface",       "priority": 1},
    }

    # All 16 bits of the Flags2 field (Odyssey) — complete coverage
    MONITORED_FLAGS2 = {
        # ── Pericolo critico (priority 8-9) ──────────────────────────────────
        6:  {"name": "LowOxygen",         "effect": "low_oxygen_warning", "priority": 9},
        7:  {"name": "LowHealth",         "effect": "low_health_warning", "priority": 9},
        11: {"name": "VeryHot",           "effect": "extreme_heat",       "priority": 8},
        10: {"name": "VeryCold",          "effect": "extreme_cold",       "priority": 8},

        # ── Pericoli ambientali (priority 5-6) ───────────────────────────────
        9:  {"name": "Hot",               "effect": "hot_warning",        "priority": 6},
        8:  {"name": "Cold",              "effect": "cold_warning",       "priority": 5},

        # ── Combattimento (priority 5) ────────────────────────────────────────
        5:  {"name": "AimDownSight",      "effect": "combat_aim",         "priority": 5},

        # ── Viaggio (priority 4) ──────────────────────────────────────────────
        12: {"name": "GlideMode",         "effect": "glide_mode",         "priority": 4},

        # ── Posizione (priority 2-3) ──────────────────────────────────────────
        15: {"name": "OnFootExterior",    "effect": "on_foot_exterior",   "priority": 3},
        4:  {"name": "OnFootOnPlanet",    "effect": "on_foot_planet",     "priority": 2},
        3:  {"name": "OnFootInStation",   "effect": "on_foot_station",    "priority": 2},
        13: {"name": "OnFootInHangar",    "effect": "on_foot_hangar",     "priority": 1},
        14: {"name": "OnFootSocialSpace", "effect": "on_foot_social",     "priority": 1},

        # ── Modalità / multiplayer (priority 1-3) ────────────────────────────
        0:  {"name": "OnFoot",            "effect": "on_foot_mode",       "priority": 3},
        1:  {"name": "InTaxi",            "effect": "in_taxi",            "priority": 3},
        2:  {"name": "InMulticrew",       "effect": "in_multicrew",       "priority": 2},
    }

    def __init__(self, status_file_path: str, callback: Callable):
        """
        Initialize Status Monitor

        Args:
            status_file_path: Path to Status.json file (usually in Journal directory)
            callback: Function to call when flags change
                      Signature: callback(flag_name: str, is_active: bool, effect_name: str, priority: int)
        """
        self.status_path = Path(status_file_path)
        self.callback = callback
        self.current_flags = 0
        self.current_flags2 = 0
        self.active_effects = {}  # flag_name -> effect_name mapping
        self.observer = None
        self.running = False
        self.last_check_time = 0
        self.check_interval = 0.3  # Debounce interval in seconds

        print(f"[StatusMonitor] Initialized with path: {self.status_path}")

    def start(self) -> bool:
        """
        Start monitoring Status.json

        Returns:
            bool: True if monitoring started successfully, False otherwise
        """
        if not self.status_path.exists():
            print(f"[StatusMonitor] WARNING: Status.json not found at {self.status_path}")
            print(f"[StatusMonitor] Will continue monitoring and wait for file to be created")
            # Don't return False - file might be created later when game starts

        # Initial read if file exists
        if self.status_path.exists():
            self._check_status()

        # Setup file watcher
        try:
            event_handler = StatusFileHandler(self._check_status_debounced)
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.status_path.parent), recursive=False)
            self.observer.start()
            self.running = True

            print(f"[StatusMonitor] Started monitoring {self.status_path.parent}")
            return True
        except Exception as e:
            print(f"[StatusMonitor] ERROR: Failed to start monitoring: {e}")
            return False

    def stop(self):
        """Stop monitoring Status.json"""
        if self.observer:
            self.observer.stop()
            self.observer.join()

        # Clear all active effects on shutdown
        for flag_name, effect_name in list(self.active_effects.items()):
            self.callback(flag_name, False, effect_name, 0)

        self.running = False
        self.active_effects.clear()
        print("[StatusMonitor] Stopped")

    def _check_status_debounced(self):
        """Debounced version of _check_status to avoid too frequent updates"""
        current_time = time.time()
        if current_time - self.last_check_time >= self.check_interval:
            self.last_check_time = current_time
            self._check_status()

    def _check_status(self):
        """Read Status.json and check for flag changes"""
        if not self.status_path.exists():
            return

        try:
            with open(self.status_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            new_flags = data.get('Flags', 0)
            new_flags2 = data.get('Flags2', 0)

            # Check Flags changes
            if new_flags != self.current_flags:
                self._process_flag_changes(
                    new_flags,
                    self.current_flags,
                    self.MONITORED_FLAGS,
                    is_flags2=False
                )
                self.current_flags = new_flags

            # Check Flags2 changes (Odyssey on-foot)
            if new_flags2 != self.current_flags2:
                self._process_flag_changes(
                    new_flags2,
                    self.current_flags2,
                    self.MONITORED_FLAGS2,
                    is_flags2=True
                )
                self.current_flags2 = new_flags2

        except json.JSONDecodeError as e:
            # File might be in the middle of being written - ignore
            pass
        except Exception as e:
            print(f"[StatusMonitor] Error reading Status.json: {e}")

    def _process_flag_changes(
        self,
        new_flags: int,
        old_flags: int,
        flag_definitions: Dict,
        is_flags2: bool = False
    ):
        """
        Process flag changes and trigger callbacks

        Args:
            new_flags: New flags value
            old_flags: Previous flags value
            flag_definitions: Dictionary of monitored flags
            is_flags2: True if processing Flags2, False for Flags
        """
        flags_name = "Flags2" if is_flags2 else "Flags"

        for bit, config in flag_definitions.items():
            flag_mask = 1 << bit
            old_state = bool(old_flags & flag_mask)
            new_state = bool(new_flags & flag_mask)

            # Only trigger callback if state changed
            if old_state != new_state:
                flag_name = config["name"]
                effect_name = config["effect"]
                priority = config["priority"]

                if new_state:
                    # Flag activated
                    print(f"[StatusMonitor] {flags_name} bit {bit} ON: {flag_name} -> Effect: {effect_name} (Priority: {priority})")
                    self.active_effects[flag_name] = effect_name
                    self.callback(flag_name, True, effect_name, priority)
                else:
                    # Flag deactivated
                    print(f"[StatusMonitor] {flags_name} bit {bit} OFF: {flag_name}")
                    if flag_name in self.active_effects:
                        del self.active_effects[flag_name]
                    self.callback(flag_name, False, effect_name, priority)

    def get_active_effects(self) -> Dict[str, str]:
        """
        Get currently active effects

        Returns:
            Dict[str, str]: Mapping of flag_name -> effect_name for all active flags
        """
        return self.active_effects.copy()

    def get_flag_state(self, flag_name: str) -> bool:
        """
        Check if a specific flag is currently active

        Args:
            flag_name: Name of the flag to check (e.g., "Overheating")

        Returns:
            bool: True if flag is active, False otherwise
        """
        return flag_name in self.active_effects


class StatusFileHandler(FileSystemEventHandler):
    """
    Watchdog event handler for Status.json file changes

    This handler triggers a callback whenever Status.json is modified.
    Includes built-in debouncing to avoid excessive updates.
    """

    def __init__(self, check_callback: Callable):
        """
        Initialize handler

        Args:
            check_callback: Function to call when Status.json changes
        """
        self.check_callback = check_callback

    def on_modified(self, event):
        """Called when a file in the watched directory is modified"""
        if event.src_path.endswith('Status.json'):
            self.check_callback()

    def on_created(self, event):
        """Called when Status.json is created (e.g., game starts)"""
        if event.src_path.endswith('Status.json'):
            print("[StatusMonitor] Status.json file created - game started")
            self.check_callback()
