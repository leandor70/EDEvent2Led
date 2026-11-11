"""
BindingsReader — Elite Dangerous keybinding parser.

Reads Custom.X.Y.binds (XML) from the standard ED Options folder,
extracts keyboard bindings, and maps each key to a functional category.

Categories (9 granular, 4 high-level groups from the Excel reference):
  Group "Ship Controls"    → flight, speed, combat, target, navigation, ship
  Group "General Controls" → interface
  Group "SRV Controls"     → srv
  Group "On Foot Controls" → onfoot

Category assignment uses two layers:
  1. Explicit FUNCTION_CATEGORIES dict (priority, covers ~200 actions)
  2. Pattern-based fallback for remaining actions (Humanoid*, Buggy*, etc.)

The key names returned match the data-key-text attributes in the
keyboard-designer.html DOM layout, enabling direct color mapping in JS.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


# ── Key name conversion: ED internal → DOM data-key-text ──────────────────
KEY_DISPLAY_MAP: Dict[str, str] = {
    # Letters
    'Key_A': 'a', 'Key_B': 'b', 'Key_C': 'c', 'Key_D': 'd',
    'Key_E': 'e', 'Key_F': 'f', 'Key_G': 'g', 'Key_H': 'h',
    'Key_I': 'i', 'Key_J': 'j', 'Key_K': 'k', 'Key_L': 'l',
    'Key_M': 'm', 'Key_N': 'n', 'Key_O': 'o', 'Key_P': 'p',
    'Key_Q': 'q', 'Key_R': 'r', 'Key_S': 's', 'Key_T': 't',
    'Key_U': 'u', 'Key_V': 'v', 'Key_W': 'w', 'Key_X': 'x',
    'Key_Y': 'y', 'Key_Z': 'z',
    # Number row
    'Key_1': '1', 'Key_2': '2', 'Key_3': '3', 'Key_4': '4',
    'Key_5': '5', 'Key_6': '6', 'Key_7': '7', 'Key_8': '8',
    'Key_9': '9', 'Key_0': '0',
    # Function keys
    'Key_F1': 'f1',   'Key_F2': 'f2',   'Key_F3': 'f3',   'Key_F4': 'f4',
    'Key_F5': 'f5',   'Key_F6': 'f6',   'Key_F7': 'f7',   'Key_F8': 'f8',
    'Key_F9': 'f9',   'Key_F10': 'f10', 'Key_F11': 'f11', 'Key_F12': 'f12',
    # Modifiers
    'Key_LeftShift':   'shift',    'Key_RightShift':   'shift',
    'Key_LeftControl': 'ctrl',     'Key_RightControl': 'ctrl',
    'Key_LeftAlt':     'alt',      'Key_RightAlt':     'alt',
    'Key_LeftWindows': 'win',      'Key_RightWindows': 'win',
    'Key_Apps':        'menu',
    # Navigation cluster
    'Key_Insert':   'ins',       'Key_Home':     'home',
    'Key_PageUp':   'page up',   'Key_Delete':   'del',
    'Key_End':      'end',       'Key_PageDown': 'page down',
    # Arrows
    'Key_UpArrow':    '\u2191',   'Key_DownArrow':  '\u2193',
    'Key_LeftArrow':  '\u2190',   'Key_RightArrow': '\u2192',
    # System keys
    'Key_Escape':      'esc',
    'Key_Tab':         'tab',
    'Key_CapsLock':    'capslock',
    'Key_BackSpace':   'backspace',
    'Key_Return':      'enter',
    'Key_Space':       ' ',
    'Key_PrintScreen': 'print screen',
    'Key_ScrollLock':  'scroll lock',
    'Key_Pause':       'pause',
    'Key_NumLock':     'num lock',
    # Punctuation
    'Key_Grave':        '`',
    'Key_Minus':        '-',
    'Key_Equals':       '=',
    'Key_LeftBracket':  '[',
    'Key_RightBracket': ']',
    'Key_BackSlash':    '\\',
    'Key_SemiColon':    ';',
    'Key_Apostrophe':   "'",
    'Key_Comma':        ',',
    'Key_Period':       '.',
    'Key_Slash':        '/',
    # Numpad — num_ prefix distinguishes from regular number row / shared symbols
    'Key_Numpad0': 'num_0',  'Key_Numpad1': 'num_1',  'Key_Numpad2': 'num_2',
    'Key_Numpad3': 'num_3',  'Key_Numpad4': 'num_4',  'Key_Numpad5': 'num_5',
    'Key_Numpad6': 'num_6',  'Key_Numpad7': 'num_7',  'Key_Numpad8': 'num_8',
    'Key_Numpad9': 'num_9',
    'Key_NumpadPlus':     'num_+',     'Key_NumpadMinus':  'num_-',
    'Key_NumpadMultiply': '\u00d7',    'Key_NumpadDivide': '\u00f7',  # × ÷ already unique
    'Key_NumpadEnter':    'num_enter', 'Key_NumpadPeriod': 'num_.',
}


# ── Explicit function → category mapping (covers ~200 known actions) ───────
# When an action is not found here, _get_category_by_pattern() is used.
FUNCTION_CATEGORIES: Dict[str, str] = {

    # ── Flight / Manoeuvring ──────────────────────────────────────────
    'YawLeftButton':                     'flight',
    'YawRightButton':                    'flight',
    'RollLeftButton':                    'flight',
    'RollRightButton':                   'flight',
    'PitchUpButton':                     'flight',
    'PitchDownButton':                   'flight',
    'ForwardThrustButton':               'flight',
    'BackwardThrustButton':              'flight',
    'UpThrustButton':                    'flight',
    'DownThrustButton':                  'flight',
    'LeftThrustButton':                  'flight',
    'RightThrustButton':                 'flight',
    'ForwardKey':                        'flight',
    'BackwardKey':                       'flight',
    'YawToRollButton':                   'flight',
    'ToggleReverseThrottleInput':        'flight',
    'DisableRotationCorrectToggle':      'flight',
    'VerticalThrustersButton':           'flight',

    # ── Speed / Throttle ──────────────────────────────────────────────
    'UseBoostJuice':                     'speed',
    'SetSpeedZero':                      'speed',
    'SetSpeed25':                        'speed',
    'SetSpeed50':                        'speed',
    'SetSpeed75':                        'speed',
    'SetSpeed100':                       'speed',
    'SetSpeedMinus25':                   'speed',
    'SetSpeedMinus50':                   'speed',
    'SetSpeedMinus75':                   'speed',
    'SetSpeedMinus100':                  'speed',
    'ToggleFlightAssist':                'speed',

    # ── Combat ───────────────────────────────────────────────────────
    'PrimaryFire':                       'combat',
    'SecondaryFire':                     'combat',
    'DeployHardpointToggle':             'combat',
    'FireChaffLauncher':                 'combat',
    'FireHeatSinkLauncher':              'combat',
    'DeployHeatSink':                    'combat',
    'UseShieldCell':                     'combat',
    'CycleFireGroupNext':                'combat',
    'CycleFireGroupPrevious':            'combat',
    'ChargeECM':                         'combat',
    'WeaponColourToggle':                'combat',
    'NightVisionToggle':                 'combat',

    # ── Targeting ────────────────────────────────────────────────────
    'SelectTarget':                      'target',
    'SelectTarget_Ahead':                'target',
    'CycleNextTarget':                   'target',
    'CyclePreviousTarget':               'target',
    'CycleNextHostileTarget':            'target',
    'CyclePreviousHostileTarget':        'target',
    'SelectHighestThreat':               'target',
    'CycleNextSubsystem':                'target',
    'CyclePreviousSubsystem':            'target',
    'TargetWingman0':                    'target',
    'TargetWingman1':                    'target',
    'TargetWingman2':                    'target',
    'SelectTargetsTarget':               'target',
    'WingNavLock':                       'target',

    # ── Navigation / FSD ─────────────────────────────────────────────
    'HyperSuperCombination':             'navigation',
    'Supercruise':                       'navigation',
    'Hyperspace':                        'navigation',
    'DisengageFSD':                      'navigation',
    'GalaxyMapOpen':                     'navigation',
    'GalaxyMapClose':                    'navigation',
    'SystemMapOpen':                     'navigation',
    'SystemMapClose':                    'navigation',
    'OrbitLinesToggle':                  'navigation',
    'TargetNextRouteSystem':             'navigation',
    'FSDMassLockEscape':                 'navigation',
    'RadarIncreaseRange':                'navigation',
    'RadarDecreaseRange':                'navigation',

    # ── Ship Systems ─────────────────────────────────────────────────
    'ShipSpotLightToggle':               'ship',
    'EjectAllCargo':                     'ship',
    'LandingGearToggle':                 'ship',
    'CargoScoopToggle':                  'ship',
    'ToggleCargoScoop':                  'ship',
    'SilentRunningToggle':               'ship',
    'SelfDestructButton':                'ship',
    'EngineColourToggle':                'ship',
    'IncreaseEnginesPower':              'ship',
    'IncreaseWeaponsPower':              'ship',
    'IncreaseSystemsPower':              'ship',
    'ResetPowerDistribution':            'ship',
    'ExplorationFSSEnter':               'ship',
    'ExplorationFSSQuit':                'ship',
    'ExplorationFSSTarget':              'ship',
    'ExplorationFSSDiscoveryScan':       'ship',
    'ExplorationFSSShowHelp':            'ship',
    'ExplorationFSSMiniMap':             'ship',
    'ExplorationSAAChangeScannedAreaViewToggle': 'ship',
    'ExplorationSAAExitThirdPerson':     'ship',

    # ── Interface / Panels ───────────────────────────────────────────
    'FocusLeftPanel':                    'interface',
    'FocusRightPanel':                   'interface',
    'FocusCommsPanel':                   'interface',
    'FocusRadarPanel':                   'interface',
    'QuickCommsPanel':                   'interface',
    'UIFocus':                           'interface',
    'Pause':                             'interface',
    'ScreenShot':                        'interface',
    'HMDReset':                          'interface',
    'HeadLookToggle':                    'interface',
    'HeadLookReset':                     'interface',
    'CycleNextPanel':                    'interface',
    'CyclePreviousPanel':                'interface',
    'MouseReset':                        'interface',
    'BlockMouseDecay':                   'interface',
    'GalnetAudio_Play_Pause':            'interface',
    'GalnetAudio_SkipForward':           'interface',
    'GalnetAudio_SkipBackward':          'interface',
    'GalnetAudio_ClearQueue':            'interface',
    'RecallDismissShip':                 'interface',

    # ── SRV — Drive / Manoeuvring ─────────────────────────────────────
    'SteerLeftButton':                   'srv_drive',
    'SteerRightButton':                  'srv_drive',
    'BuggyRollLeftButton':               'srv_drive',
    'BuggyRollRightButton':              'srv_drive',
    'BuggyPitchUpButton':                'srv_drive',
    'BuggyPitchDownButton':              'srv_drive',
    'BuggyToggleReverseThrottleInput':   'srv_drive',
    'IncreaseSpeedButtonMax':            'srv_drive',
    'DecreaseSpeedButtonMax':            'srv_drive',
    'ToggleDriveAssist':                 'srv_drive',
    'AutoBreakBuggyButton':              'srv_drive',
    'VerticalThrustersButton_Buggy':     'srv_drive',

    # ── SRV — Combat / Weapons ────────────────────────────────────────
    'BuggyPrimaryFireButton':            'srv_combat',
    'BuggySecondaryFireButton':          'srv_combat',
    'BuggyCycleFireGroupNext':           'srv_combat',
    'BuggyCycleFireGroupPrevious':       'srv_combat',
    'SelectTarget_Buggy':                'srv_combat',

    # ── SRV — Turret & Power ──────────────────────────────────────────
    'ToggleBuggyTurretButton':           'srv_turret',
    'BuggyTurretYawLeftButton':          'srv_turret',
    'BuggyTurretYawRightButton':         'srv_turret',
    'BuggyTurretPitchUpButton':          'srv_turret',
    'BuggyTurretPitchDownButton':        'srv_turret',
    'IncreaseEnginesPower_Buggy':        'srv_turret',
    'IncreaseWeaponsPower_Buggy':        'srv_turret',
    'IncreaseSystemsPower_Buggy':        'srv_turret',
    'ResetPowerDistribution_Buggy':      'srv_turret',

    # ── SRV — Utility ────────────────────────────────────────────────
    'HeadlightsBuggyButton':             'srv_util',
    'ToggleCargoScoop_Buggy':            'srv_util',
    'EjectAllCargo_Buggy':               'srv_util',

    # ── On Foot — Movement ────────────────────────────────────────────
    'HumanoidForwardButton':             'onfoot_move',
    'HumanoidBackwardButton':            'onfoot_move',
    'HumanoidStrafeLeftButton':          'onfoot_move',
    'HumanoidStrafeRightButton':         'onfoot_move',
    'HumanoidSprintButton':              'onfoot_move',
    'HumanoidCrouchButton':              'onfoot_move',
    'HumanoidJump':                      'onfoot_move',
    'HumanoidJumpButton':                'onfoot_move',
    'HumanoidWalkButton':                'onfoot_move',

    # ── On Foot — Combat / Weapons ────────────────────────────────────
    'HumanoidPrimaryFireButton':         'onfoot_combat',
    'HumanoidSecondaryFireButton':       'onfoot_combat',
    'HumanoidMeleeButton':               'onfoot_combat',
    'HumanoidThrowGrenadeButton':        'onfoot_combat',
    'HumanoidReloadButton':              'onfoot_combat',
    'HumanoidSwitchWeapon':              'onfoot_combat',
    'HumanoidSelectPrimaryWeaponButton': 'onfoot_combat',
    'HumanoidSelectSecondaryWeaponButton': 'onfoot_combat',
    'HumanoidSelectUtilityWeaponButton': 'onfoot_combat',
    'HumanoidHideWeaponButton':          'onfoot_combat',
    'HumanoidToggleShieldsButton':       'onfoot_combat',
    'HumanoidSelectNextGrenadeTypeButton':     'onfoot_combat',
    'HumanoidSelectPreviousGrenadeTypeButton': 'onfoot_combat',

    # ── On Foot — Items / Equipment ───────────────────────────────────
    'HumanoidHealthPack':                'onfoot_item',
    'HumanoidBattery':                   'onfoot_item',
    'HumanoidItemWheelButton':           'onfoot_item',
    'HumanoidClearAuthorityLevel':       'onfoot_item',

    # ── On Foot — Interaction / UI ────────────────────────────────────
    'HumanoidPrimaryInteractButton':     'onfoot_interact',
    'HumanoidSecondaryInteractButton':   'onfoot_interact',
    'HumanoidEmoteWheelButton':          'onfoot_interact',
    'HumanoidOpenAccessPanelButton':     'onfoot_interact',
    'HumanoidConflictContextualUIButton': 'onfoot_interact',
    'HumanoidToggleMissionHelpPanelButton': 'onfoot_interact',
    'HumanoidUtilityWheelCycleMode':     'onfoot_interact',
}

# ── Pattern-based fallback prefixes → category ────────────────────────────
# Applied when an action is NOT in FUNCTION_CATEGORIES.
# Order matters: first match wins.
_PATTERN_RULES = [
    # On foot — unknown Humanoid* actions default to interaction
    ('Humanoid',               'onfoot_interact'),
    # SRV — unknown Buggy* actions default to utility
    ('Buggy',                  'srv_util'),
    # Exploration
    ('ExplorationFSS',         'ship'),
    ('ExplorationSAA',         'ship'),
    # Navigation maps
    ('GalaxyMap',              'navigation'),
    ('SystemMap',              'navigation'),
    # Camera / interface / photo mode
    ('FreeCam',                'interface'),
    ('VanityCamera',           'interface'),
    ('PhotoCamera',            'interface'),
    ('FixCamera',              'interface'),
    ('Cam',                    'interface'),   # CamTranslate*, CamYaw*, CamPitch*, CamZoom*
    ('MoveCamera',             'interface'),
    ('YawCamera',              'interface'),
    ('RollCamera',             'interface'),
    ('PitchCamera',            'interface'),
    ('RotateCamera',           'interface'),
    ('MoveCameraForwardKeys',  'interface'),
    # Placement / settlement
    ('MoveFreeCam',            'interface'),   # MoveFreeCamForward/Back/Left/Right...
    ('PlacementCam',           'interface'),
    ('MovePlacementCam',       'interface'),
    ('PitchPlacementCamera',   'interface'),
    ('YawPlacementCamera',     'interface'),
    ('PlaceSettlement',        'interface'),
    ('RotateSettlement',       'interface'),
    ('ChangeConstruction',     'interface'),
    ('MultiCrewCockpit',       'interface'),
    ('MultiCrewToggle',        'interface'),
    ('MultiCrewPrimary',       'combat'),
    ('MultiCrewSecondary',     'combat'),
    ('PlayerHUD',              'interface'),
    ('FStop',                  'interface'),   # camera depth-of-field
    ('Cycle',                  'interface'),   # CycleNextPage, CyclePreviousPage
    ('ToggleButtonUpInput',    'interface'),
    ('ToggleReverseThrottleInputFreeCam', 'interface'),
    # Orders (wing commands)
    ('Order',                  'interface'),
    # Store / vanity
    ('Store',                  'interface'),
    ('CommanderCreator',       'interface'),
    # Comms / UI
    ('QuickComms',             'interface'),
    ('Focus',                  'interface'),
    ('UI_',                    'interface'),
    # Galnet audio
    ('GalnetAudio',            'interface'),
]

# ── Suffix-based patterns (action ends with suffix) ───────────────────────
_SUFFIX_RULES = [
    ('_Buggy',    'srv'),
]


def _get_category_by_pattern(action: str) -> str:
    """
    Return a category based on action name prefix/suffix patterns.
    Returns 'other' if no pattern matches.
    """
    for prefix, cat in _PATTERN_RULES:
        if action.startswith(prefix):
            return cat
    for suffix, cat in _SUFFIX_RULES:
        if action.endswith(suffix):
            return cat
    return 'other'


def get_action_category(action: str) -> str:
    """
    Public helper: return the category for any ED action name.

    Checks explicit dict first, falls back to pattern matching.
    """
    return FUNCTION_CATEGORIES.get(action) or _get_category_by_pattern(action)


# ── Category → game mode ──────────────────────────────────────────────────
CATEGORY_MODE: Dict[str, str] = {
    'flight':          'ship',
    'speed':           'ship',
    'combat':          'ship',
    'target':          'ship',
    'navigation':      'ship',
    'ship':            'ship',
    'interface':       'universal',
    'srv_drive':       'srv',
    'srv_combat':      'srv',
    'srv_turret':      'srv',
    'srv_util':        'srv',
    'onfoot_move':     'onfoot',
    'onfoot_combat':   'onfoot',
    'onfoot_item':     'onfoot',
    'onfoot_interact': 'onfoot',
    # Legacy single-category fallback (kept for backward compat)
    'srv':    'srv',
    'onfoot': 'onfoot',
    'other':  'other',
}


# ── Category color palette (RGB tuples) ───────────────────────────────────
# Colors grouped by the 4 high-level Excel categories:
#   Ship Controls    → blues / reds / oranges
#   General Controls → violet
#   SRV Controls     → teal
#   On Foot Controls → lime/green
CATEGORY_COLORS: Dict[str, tuple] = {
    # Ship Controls
    'flight':          (0,   119, 255),   # #0077FF  blue
    'speed':           (0,   204, 255),   # #00CCFF  cyan
    'combat':          (255,  30,  30),   # #FF1E1E  red
    'target':          (255, 120,   0),   # #FF7800  orange
    'navigation':      (0,   220, 100),   # #00DC64  green
    'ship':            (255, 210,   0),   # #FFD200  yellow
    # General
    'interface':       (160,  80, 255),   # #A050FF  violet
    # SRV — reuse ship palette (modes are mutually exclusive)
    'srv_drive':       (0,   119, 255),   # #0077FF  blue   (like flight)
    'srv_combat':      (255,  30,  30),   # #FF1E1E  red    (like combat)
    'srv_turret':      (255, 120,   0),   # #FF7800  orange (like target)
    'srv_util':        (255, 210,   0),   # #FFD200  yellow (like ship)
    # On Foot — reuse ship palette
    'onfoot_move':     (0,   119, 255),   # #0077FF  blue   (like flight)
    'onfoot_combat':   (255,  30,  30),   # #FF1E1E  red    (like combat)
    'onfoot_item':     (255, 120,   0),   # #FF7800  orange (like target)
    'onfoot_interact': (160,  80, 255),   # #A050FF  violet (like interface)
    # Legacy / fallback
    'srv':             (0,   220, 180),   # #00DCB4  teal
    'onfoot':          (150, 255,  60),   # #96FF3C  lime
    'other':           (80,   80,  80),   # #505050  dark gray
}


class BindingsReader:
    """
    Reads Custom.X.Y.binds and produces a key → category mapping.

    Usage:
        reader = BindingsReader()
        result = reader.read()                    # auto-detect
        result = reader.read('/path/to/file.binds')
    """

    _SEARCH_PATHS = [
        Path(os.environ.get('LOCALAPPDATA', '')) /
        'Frontier Developments' / 'Elite Dangerous' / 'Options' / 'Bindings',
    ]

    @staticmethod
    def _version_key(path: Path):
        import re
        m = re.search(r'Custom\.(\d+)\.(\d+)\.binds$', path.name, re.IGNORECASE)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    def find_bindings_file(self) -> Optional[Path]:
        for base in self._SEARCH_PATHS:
            if not base.exists():
                continue
            custom_files = sorted(
                base.glob('Custom*.binds'),
                key=self._version_key,
                reverse=True,
            )
            if custom_files:
                return custom_files[0]
            any_files = sorted(
                base.glob('*.binds'),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if any_files:
                return any_files[0]
        return None

    def read(self, file_path: Optional[str] = None) -> dict:
        """
        Parse keybindings and return categorised key assignments.

        Returns:
            {
                'success':       bool,
                'file_path':     str,
                'categories':    { display_key: category },   (ship+universal)
                'bindings':      { display_key: func_name },  (ship+universal)
                'modes':         { mode: { display_key: {category, func} } },
                'colors':        { category: [r, g, b] },
                'stats':         { category: count },
                'categorised':   int,
                'uncategorised': int,
                'error':         str (only on failure)
            }
        """
        # ── Resolve file path ──────────────────────────────────────────────
        if file_path:
            path = Path(file_path)
        else:
            path = self.find_bindings_file()

        if path is None or not path.exists():
            return {
                'success':   False,
                'error':     'No .binds file found. '
                             'Expected at: %LOCALAPPDATA%\\Frontier Developments\\'
                             'Elite Dangerous\\Options\\Bindings\\Custom.4.2.binds',
                'file_path': str(path) if path else None,
            }

        try:
            tree = ET.parse(str(path))
            root = tree.getroot()
        except ET.ParseError as e:
            return {'success': False, 'error': f'XML parse error: {e}', 'file_path': str(path)}

        # ── Parse all bindings ─────────────────────────────────────────────
        # mode_data: { mode → { display_key → { category, func } } }
        mode_data: Dict[str, Dict[str, dict]] = {
            'ship':      {},
            'srv':       {},
            'onfoot':    {},
            'universal': {},
            'other':     {},
        }

        for element in root:
            func_name = element.tag
            category  = get_action_category(func_name)
            mode      = CATEGORY_MODE.get(category, 'other')

            for slot in ('Primary', 'Secondary'):
                slot_el = element.find(slot)
                if slot_el is None:
                    continue
                device = slot_el.get('Device', '')
                key    = slot_el.get('Key', '')

                if device != 'Keyboard' or not key:
                    continue

                # Skip modifier combinations (Shift+X, Ctrl+Y, etc.) —
                # only plain key presses should be shown on the keyboard map.
                if slot_el.find('Modifier') is not None:
                    continue

                display = KEY_DISPLAY_MAP.get(key)
                if display is None:
                    continue

                bucket   = mode_data[mode]
                existing = bucket.get(display)

                # Primary wins over Secondary; categorised wins over 'other'
                if existing is None:
                    bucket[display] = {'category': category, 'func': func_name}
                elif existing['category'] == 'other' and category != 'other':
                    bucket[display] = {'category': category, 'func': func_name}

        # ── Build flat output (ship + universal as default view) ───────────
        categories: Dict[str, str] = {}
        bindings:   Dict[str, str] = {}
        for key, entry in {**mode_data['ship'], **mode_data['universal']}.items():
            categories[key] = entry['category']
            bindings[key]   = entry['func']

        # ── Stats ──────────────────────────────────────────────────────────
        stats: Dict[str, int] = {}
        for bucket in mode_data.values():
            for entry in bucket.values():
                cat = entry['category']
                stats[cat] = stats.get(cat, 0) + 1

        colors        = {cat: list(rgb) for cat, rgb in CATEGORY_COLORS.items()}
        modes_serial  = {
            mode: {key: {'category': e['category'], 'func': e['func']}
                   for key, e in bucket.items()}
            for mode, bucket in mode_data.items()
        }
        categorised   = sum(v for k, v in stats.items() if k != 'other')
        uncategorised = stats.get('other', 0)

        return {
            'success':        True,
            'file_path':      str(path),
            'categories':     categories,
            'bindings':       bindings,
            'modes':          modes_serial,
            'colors':         colors,
            'stats':          stats,
            'categorised':    categorised,
            'uncategorised':  uncategorised,
        }
