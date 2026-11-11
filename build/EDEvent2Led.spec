# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for ED:Event2Led
#
# One-folder build (not one-file) so that:
#   - web/ sits next to the .exe and is easy to update
#   - config/ can be created/modified by the user at runtime
#   - startup is fast (no self-extraction)
#
# Usage:
#   pyinstaller build/EDEvent2Led.spec
#
# Output:
#   dist/EDEvent2Led/          <- this whole folder is what you ship
#     EDEvent2Led.exe
#     web/
#     config/                  <- default configs (first-run only)
#     _internal/               <- Python + dependencies (PyInstaller 6+)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from pathlib import Path
import sys

ROOT = Path(SPECPATH).parent   # project root (build/ -> ..)

# ── Collect eel's web bottle assets ──────────────────────────────────────
eel_datas = collect_data_files('eel')

# ── Application data files ────────────────────────────────────────────────
# web/     : full frontend (HTML, JS, CSS, fonts, images, i18n JSON)
# config/  : default configs shipped with the installer (user will modify these)
app_datas = [
    (str(ROOT / 'web'),    'web'),
    (str(ROOT / 'config'), 'config'),
    # README in the root of dist/EDEvent2Led/
    (str(ROOT / 'build' / 'README.dist.txt'), '.'),
]

# ── Hidden imports ────────────────────────────────────────────────────────
# Libraries that PyInstaller can't detect via static analysis
hidden_imports = [
    # Eel internals
    'eel',
    'bottle',
    'gevent',
    'geventwebsocket',
    # Built-in OpenRGB SDK client (replaces openrgb-python, GPLv3)
    'utils.openrgb_client',
    # watchdog backends (Windows)
    'watchdog',
    'watchdog.observers',
    'watchdog.observers.winapi',
    'watchdog.events',
    # Application modules (src/ subpackages)
    'api',
    'api.settings_api',
    'api.effects_api',
    'api.events_api',
    'api.keyboard_api',
    'api.devices_api',
    'api.monitoring_api',
    'api.status_monitor_api',
    'api.bindings_api',
    'api.device_config_api',
    'api.logs_api',
    'api.profiles_api',
    'api.topology_api',
    'api.update_api',
    'core',
    'core.base_effects',
    'core.visual_effect_library',
    'core.visual_effect_renderer',
    'core.color_scheme_library',
    'core._active_effect',
    'core._bbox',
    'core._io_batcher',
    'effects',
    'effects.unified_manager',
    'effects.keyboard_matrix_2d',
    'effects.linear_1d',
    'effects.spatial_effects_1d',
    'effects.spatial_effects_2d',
    'effects.gradient_2d',
    'effects.pulse_2d',
    'effects.corner_gradient_2d',
    'effects.device_topology',
    'effects.k7_matrix_map',
    'journal',
    'journal.journal_reader',
    'journal.event_processor',
    'journal.status_monitor',
    'journal.bindings_reader',
    'utils',
    'utils.log_buffer',
    'utils.unicode_safe',
    'utils.paths',
    'utils.color_utils',
    'utils.openrgb_safe',
    # Ambilight + screen capture
    'api.ambilight_api',
    'effects.ambilight_service',
    'core.screen_capturer_service',
    'numpy',
    'mss',
    'mss.windows',
    # System tray
    'pystray',
    'pystray._win32',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    # Version info baked at build time by build_pyinstaller.ps1
    '_version',
]

a = Analysis(
    [str(ROOT / 'src' / 'main.py')],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=eel_datas + app_datas,
    hiddenimports=hidden_imports,
    hookspath=[str(ROOT / 'build' / 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev / test only (unittest escluso: pyparsing.testing lo importa indirettamente via eel)
        'pytest', 'doctest',
        # GUI toolkits not used
        'tkinter', 'PyQt6', 'wx',
        # Heavy scientific libs not needed (numpy is NOW required by ambilight)
        'pandas', 'matplotlib', 'scipy',
        # IPython / Jupyter
        'IPython', 'jupyter',
        # openrgb-python is GPLv3 and replaced by utils.openrgb_client:
        # never bundle it, even if installed in the build environment
        'openrgb',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EDEvent2Led',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'build' / 'icon.ico'),   # see build/README.md for icon generation
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EDEvent2Led',
)

# ── Post-build: move user-facing dirs from _internal/ to dist root ─────────
# PyInstaller 6+ places all datas inside _internal/ by default.
# We move config/, web/ and README.dist.txt to the root so that:
#   - config/ is easy for users to find and edit
#   - web/ is where main.py expects it (get_base_dir() / 'web')
#   - README.txt appears in the top-level folder
import shutil as _shutil

_dist_root = Path(DISTPATH) / 'EDEvent2Led'
_internal  = _dist_root / '_internal'

for _dirname in ('config', 'web'):
    _src = _internal / _dirname
    _dst = _dist_root / _dirname
    if _src.exists():
        if _dst.exists():
            _shutil.rmtree(_dst)
        _shutil.copytree(_src, _dst)
        _shutil.rmtree(_src)

# README.dist.txt → README.txt at dist root
_src_readme = _internal / 'README.dist.txt'
_dst_readme = _dist_root / 'README.txt'
if _src_readme.exists():
    _shutil.copy2(_src_readme, _dst_readme)
    _src_readme.unlink()

# Rimuovi web/node_modules (dev-only, non serve a runtime)
_web_node_modules = _dist_root / 'web' / 'node_modules'
if _web_node_modules.exists():
    _shutil.rmtree(_web_node_modules)
