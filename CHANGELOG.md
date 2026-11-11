# Changelog

All notable changes to ED:Event2Led will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-11-11

The source code of ED:Event2Led is now public, under the PolyForm Noncommercial
License 1.0.0, and the app tells you when a new version is out.

### Added

- **New version notice.** At startup the app asks GitHub whether a newer release
  exists. If it does, a notice shows the new version with a link to its release page,
  once per session; "Don't remind me for this version" hides it until the next one.
  Only the app name and version are sent. The check can be turned off in
  Configuration → System Settings → Updates; the Data & Privacy text of the About
  page now mentions it.

### Changed

- **License: PolyForm Noncommercial 1.0.0 (source-available).** The source code is
  now public. You may read, run, modify and share it for any noncommercial purpose;
  streaming and videos of your gameplay remain allowed, including on monetized
  channels. See `NOTICE.md` and `THIRD-PARTY.md`; the Windows package now includes
  them, with the license texts of the bundled fonts and libraries. Releases up to
  1.3.0 stay under the freeware license they shipped with.

## [1.3.0] - 2026-11-11

This release replaces the bundled OpenRGB library with a built-in client, and fixes
an ambilight that covered running effects, an ambilight that flickered on text, and an
OpenRGB restart that went unnoticed.

### Changed

- **Built-in OpenRGB client.** ED:Event2Led no longer bundles the third-party
  `openrgb-python` library. Its own client, written from the public OpenRGB SDK
  protocol description, sends exactly the same packets: this was checked byte for byte
  against packets recorded from the library. It never asks OpenRGB for its plugin
  list, the request that used to fail with some plugins installed. Writing LED frames
  is about 40% faster, and the app now shows up as "ED:Event2Led" in the SDK client
  list of OpenRGB.

### Fixed

- **Ambilight wrote over running effects** after "Test connection" on the
  Configuration page, or after a reconnection to OpenRGB. The ambilight kept asking
  the previous connection whether an effect was playing, which always answered no. For
  the same reason, game events did nothing after a reconnection, and every
  "Test connection" left one more connection open to OpenRGB. All of these now follow
  the new connection.
- **Ambilight flickered between unrelated colors** on dark content with colored text,
  such as a chat window, an IDE or a terminal, for example when a text cursor blinked.
  The percentile strategies, including the default "Adaptive + EMA", took the color
  of a single pixel. They now use the average of the brightest 20% of the pixels,
  which changes smoothly instead of jumping.
- **OpenRGB restarted while the app was open** was not detected. Its port answered
  again, but the app's connection was dead: effects failed and the automatic
  reconnection never started. The status check now tests the app's own connection.

## [1.2.0] - 2026-11-11

This release fixes several serious bugs: a crash that blocked the OpenRGB connection,
an ambilight that lit the wrong side of the screen, and effects and calibration that did
not match the Topology Editor drawing. **Updating is recommended for every user**, and
especially for ambilight users.

### Fixed — critical

- **OpenRGB connection failed with some OpenRGB plugins installed.**
  If OpenRGB had a plugin the client library did not know (for example the
  *OpenRGB Hardware Sync Plugin*), the connection stopped with
  `OpenRGB connection failed: 'OpenRGB Hardware Sync Plugin'`. No device was detected,
  and no effect could run.
  The bundled `openrgb-python` is now 0.3.8, which skips unknown plugins instead of failing.
  *Who was affected:* anyone with an unrecognized OpenRGB plugin installed. The app could
  not be used at all until the plugin was removed.

- **Ambilight: the left and right strips showed the screen upside down.**
  The editor measures y upwards, while a captured frame has row 0 at the top. Vertical
  strips therefore read the bottom of the screen on their top LEDs, and the other way round.
  Strips mounted with their first LED at the bottom were reversed a second time, because
  their direction was guessed from the zone name instead of the real LED order.
  Both are now derived from geometry.

- **Ambilight: the screen side a strip followed depended on the zone name.**
  A zone had to be called something like "MonitorTop" or "Left" to be sampled correctly.
  Any other name, or a strip moved in the editor, sampled the wrong edge or nothing at all.
  The side is now decided only by **where the LEDs are drawn** relative to the new
  **screen rectangle** of the Topology Editor:
  - LEDs on or near an edge follow that edge;
  - LEDs inside the rectangle follow the point of the screen under them;
  - LEDs outside are not touched.

  If no rectangle is saved, one is computed from the active devices with the
  proportions of the real screen.

- **Ambilight overwrote LEDs it did not use.**
  The whole device was rewritten on every frame. LEDs outside the screen, or in
  disabled zones, were forced off, and fought with effects and with OpenRGB.
  Now only the LEDs in use are written, with one packet per fully covered OpenRGB zone.
  A LED that leaves the ambilight (zone disabled, rectangle moved) is turned off once,
  then left alone.

- **Ambilight: zones with the same name switched on and off together.**
  Zones were enabled by name and LED offsets were indexed by zone index, so repeated
  names or indexes overwrote each other.
  They are now tracked by zone index and by position. Settings saved by earlier
  versions are still read.

- **Topology calibration did not match the editor.**
  The rings lit on the hardware were computed by a separate backend routine. It used
  different LED centres, ignored reversed zones, and placed the centre differently.
  As a result, the LEDs shown white in the editor could light up red, and the blinking
  centre LED could be off by a few positions.
  The editor now sends the exact plan it draws (colour of every LED and the centre LED),
  and the hardware shows the same thing.
  Errors during calibration are now reported instead of failing silently.

- **Spatial effects were placed differently from the editor.**
  The effect engine computed LED positions with its own rules: only 0/90/180/270°
  rotations, no support for reversed zones, LEDs anchored at their start instead of
  their centre. A custom effect centre was also measured on a different bounding box.
  Waves, explosions and centred effects could therefore start from a point other than
  the one chosen in the editor.
  Effects, calibration and ambilight now share **one geometry**, identical to the
  editor's: any rotation angle, reversed zones, LED centres.

### Fixed — other

- **Effect centre moved with the zones.** Moving or resizing a zone in the Topology
  Editor dragged the effect centre with it. The centre now stays fixed in the scene
  until you move the crosshair yourself.
- **23 notifications showed raw translation keys** (e.g. `notifications.event_saved`)
  instead of the message, in every language. Affected messages include
  "Event saved", "Preset loaded" and "Reconnection failed".
- **Topology Editor and side menu were not translated.** They are now fully translated
  in all 5 languages. Before, the presets were in Italian for everyone, and on the
  Ambilight page the cards could show raw keys when loaded before the translations.
- **Manual:**
  - "Show Guide" did nothing on the Home and Ambilight pages;
  - contextual help opened the Italian manual whatever the UI language, and did not
    change chapter when the manual was already open;
  - the English manual showed an Italian table of contents.
- **"Reset All" in the Topology Editor** asked to "restore default positions", but it
  actually reloads the last saved topology. The confirmation now says so.
- **`start.bat`** reported "Python embedded not found" in source installs. It now falls
  back to `venv\` when the embedded Python is missing.

### Added

- **Topology Editor:**
  - the canvas now uses the whole window;
  - LEDs are drawn as contiguous cells as wide as their spacing, so a strip looks like
    the real one;
  - a screen rectangle panel sets where the monitor is in the scene, for the ambilight.
- **Ambilight:** a **Test idle** button stops running effects and hands the LEDs to the
  ambilight, to check the result without waiting for the idle timeout.
- **Manual (Italian and English):**
  - chapter 6 (Topology Editor) is rewritten;
  - new chapter 12 covers the Ambilight;
  - the glossary and FAQ are updated.

### Changed

- **One visual theme on all pages:**
  - every dropdown uses the semi-transparent "glass" menu of the Configuration page,
    with full keyboard support;
  - toggles are now vertically centred in their track;
  - duplicated per-page styles have been removed.

## [1.1.1] - 2026-11-04

### Added

- **License**: ED:Event2Led is now distributed as freeware (personal, non-commercial use;
  no resale and no redistribution outside the official release page). The `LICENSE` file
  is included in the release package and summarized in `README.txt`.

## [1.1.0] - 2026-10-25

### Changed

- **Device keys**: devices that share a name (e.g. two identical RAM modules) now get
  distinct keys, `Name::type` for the first and `Name::type#2`, `#3`... for the others,
  in `device_config.json`, `ambilight_config.json` and `device_topologies.json`.
  The topology editor used to key topologies by position (`Name::linear::6`) and the
  ambilight by name only, so the ambilight did not follow what the editor saved.
  **Migration is automatic** at the first start with OpenRGB connected: the old content
  of each changed file is kept as `<file>.v1.bak.json`, and the file is marked
  `"device_keys": 2`. Entries that cannot be matched to a device are left untouched
  and reported in the log. Topologies saved with a position index are matched only if
  the device now at that position has the same name and type.
### Fixed

- Saving a topology now refreshes the ambilight zones and the effect controllers
  without restarting the app.
- Topology and hardware are checked at every start and reconnection: zones added or
  removed, or LED counts changed in OpenRGB, are re-synced (positions, rotation and
  zone names set in the editor are kept; `config/device_topologies.sync.bak.json`
  is written before the first change). A remaining mismatch is reported once in the log.
- Devices with segmented zones (E1.31/ARGB) get unique zone indexes; saved topologies
  with repeated indexes are renumbered by position.
- Ambilight: DXGI capture is restarted when its thread dies (display mode change, lock
  screen, driver reset), also when dxcam clears its own capture thread after a crash
  (the LEDs used to stay frozen); capture restart, FPS changes and `stop()` no longer
  race with the frame grab; frames no longer need OpenCV (`BGRA`); the capture backend
  fallback no longer fails when `windows-capture` or `dxcam` is missing; a capturer swap
  racing with `stop()` no longer leaves an orphan capturer.
- Ambilight is paused and its LEDs are turned off during topology calibration and
  device identification (flash); leaving the topology editor stops an active
  calibration.

## [2.0.0-phase1] - 2026-03-24

### 🎉 Major Features

#### Phase 1.1: Coordinate Normalization Infrastructure
- **GlobalBoundingBox System**: Unified coordinate space [0,1] for all devices
- **Device-Independent Effects**: Effects work across keyboard, mouse, LED strips without modification
- **Multi-Device Synchronization**: Shared coordinate space for simultaneous multi-device effects
- **15 Effects Migrated**: Wave, Bloom, Explosion, Fire, Aurora, Matrix Rain, Ocean Waves, Plasma, Lightning, Glitch, Parallax Stars, Bump, Directional Flash, Color Cycle, Two Color Nuance

#### Phase 1.2: Directional Parameters
- **8-Way Direction Control**: Cardinal (top/down/left/right) + Diagonal (tl/tr/bl/br)
- **Fire Effect Directions**: Bottom→Top (realistic) and Top→Bottom (inverted) combustion
- **Color Cycle Directions**: Full 8-way support with world coordinate awareness
- **UI Direction Selector**: Visual direction picker in Effect Step parameters

#### Topology Editor
- **Visual Device Layout**: Interactive canvas for positioning devices
- **Rotation Support**: 0°, 90°, 180°, 270° for axis-aligned orientations
- **Drag & Drop**: Position devices in 2D space matching physical setup
- **Bounding Box Preview**: Real-time visualization of device extents
- **JSON Persistence**: Topology saved to `config/device_topologies.json`

#### Event Definitions System
- **239 Events Extracted**: Complete catalog from Elite Dangerous Journal Manual Excel
- **Event Badges**: Visual indicators in Effect Editor showing associated events
- **Tooltips with Descriptions**: Hover for full event explanations
- **Reverse Lookup**: Find which events trigger a specific effect

### 🌟 Added

#### Backend
- **Topology API** (`src/api/topology_api.py`): Load/save device layouts
- **OpenRGB Safe Utils** (`src/utils/openrgb_safe.py`): Connection management helpers
- **Topology-Aware LINEAR Effects**: World coordinate support in `linear_1d.py`
- **Coordinate Normalization Methods**: `_get_normalized_coords()`, `get_all_normalized_positions()`
- **BaseEffectParams.use_normalized**: Flag to enable normalized coordinate mode

#### Frontend
- **Topology Editor Page** (`web/topology-editor.html`, `web/js/topology-editor.js`)
- **Event Definitions JSON** (`web/config/event_definitions.json`): 239 event descriptions
- **Tour Guide System** (`web/js/tour-guide.js`): Interactive UI walkthroughs
- **Glassmorphism Toggle**: "Show NEW" filter for quick-created effects
- **Event Badge Display**: In Effect Editor panel (larger, more visible than sidebar)
- **Keyboard Return Button**: Auto-disable when last step is keyboard effect

#### UI/UX
- **Offline Font Bundle**: Orbitron + Rajdhani WOFF2 (no CDN dependency)
- **Custom CSS Files**: `web/css/fonts.css`, `web/css/sci-fi-theme.css`
- **Tour Guides**: Step-by-step walkthroughs for Effects Editor, Events, Topology Editor
- **Filter Toggle**: Clear glassmorphism switch instead of ambiguous button

#### i18n
- **Complete Translations**: All new features translated to 5 languages (en, it, de, es, fr)
- **Event Tooltips**: Translated descriptions for all UI elements
- **Tour Guides**: Multi-language support for all interactive tours

### 🔧 Changed

#### Effects System
- **Fire Effect**: Now supports `direction` parameter ('down' or 'top')
- **Color Cycle Effect**: Rewritten with world coordinate awareness (8-way directions)
- **Aurora Effect**: Full coverage fix (height, tail_length, wave_amplitude adjustments)
- **Matrix Rain Effect**: Bottom coverage fix (head position reset logic)
- **Parallax Stars Effect**: Added directional parameter support (left/right)
- **Glitch Effect**: Added `get_led_color()` method to Linear1D for smooth transitions

#### UI Improvements
- **Event Badges Position**: Moved from sidebar (small) to editor panel (large, readable)
- **Direction UI**: Added `directionOptions` system to disable unsupported direction buttons
- **Toggle Switch**: Replaced "NEW" button with glassmorphism toggle + label

### 🐛 Fixed

#### Critical Bugs
- **Global Wave Rotation Bug**: Removed double-correction in `_calculate_wave_position()` (rotation already handled by `get_led_world_position()`)
- **Aurora ZeroDivisionError**: Horizontal device detection (`y_span < 1.0`) with fallback to `x_span`
- **Matrix Rain Bottom LEDs**: Fixed premature drop reset (now checks head position, not tail)
- **Plasma Center Calculation**: Fixed `cy = (min_y + min_y)/2` → `cy = (min_y + max_y)/2`
- **DirectionalFlash & Plasma Animation**: Converted from broken `render_frame()` to proper `_run_animation()` pattern

#### Data Structure
- **Event Mappings Array→Object**: Fixed badge showing "7" instead of "FSDJump" by normalizing API array to object in `loadEventMappings()`

### 📚 Documentation

#### New Docs
- **COORDINATE_NORMALIZATION_DESIGN.md**: Complete architecture design
- **EFFECTS_SYSTEM_ROADMAP.md**: Phase 1-4 implementation plan
- **HARDWARE_COMPATIBILITY_STRATEGY.md**: Multi-hardware testing strategy
- **CHANGELOG.md**: This file

#### Updated Docs
- **README.md**: Updated features, roadmap, Phase 1 summary
- **UI_IMPROVEMENT_PLAN.md**: Tour guides, topology editor documentation

### 🛠️ Technical Details

#### Architecture Patterns
- **1D Effects Animation Loop**: Standardized `_run_animation()` + `_apply_color_map()` pattern
- **Coordinate Mapping**: MATRIX (row,col)→world, LINEAR (topology JSON), SINGLE (0,0)
- **Direction Inversions**: Empirically validated formulas for cardinaldirections (Y-inverted) and diagonals (X+Y inverted)

#### Performance
- **Effect Count**: 18 primitive effects (15 topology-aware, 3 basic/special)
- **Topology Support**: Full 1D + 2D coverage for spatial effects
- **Coordinate Overhead**: Minimal (~5% frame time for normalization calculations)

### 🔬 Testing
- **tools/extract_event_definitions.py**: Excel→JSON extraction script
- **tools/update_new_filter_translation.py**: i18n update script for toggle
- **tools/test_coordinate_normalization.py**: Comprehensive test suite (4 test cases, 100% pass)

---

## [2.0.0-critical] - 2026-02-28

### Added
- Offline bundle (fonts, assets)
- Animation pause system
- Keyboard shortcuts framework
- Status effects mapping
- Library categories
- Fade-in UX toggle
- Port configuration
- Installer package

---

## [2.0.0-beta] - 2026-02-15

### Added
- Status effects system
- Library effect categories
- Fade-in toggle for primitive effects
- Unicode handling improvements

---

## [2.0.0-alpha] - 2025-12-18

### Added
- Initial release
- Visual Effects system
- Effect Library editor
- Keyboard Matrix Simulator
- Event Mapper v2
- Color Schemes support
- PyQt6 UI (later removed)
- OpenRGB integration

---

**Note**: Pre-Phase 1 versions focused on core functionality. Phase 1 (March 2026) introduced coordinate normalization, topology awareness, and comprehensive UI improvements.
