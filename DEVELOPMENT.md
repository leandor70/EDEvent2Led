# ED:Event2Led - Elite Dangerous RGB Lighting Controller

**Real-time RGB lighting effects synchronized with Elite Dangerous game events.**

![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-green)

---

## Overview

ED:Event2Led monitors Elite Dangerous journal files in real-time and triggers customizable RGB lighting effects on your PC hardware (keyboard, mouse, RAM, case lighting, etc.) based on in-game events using OpenRGB.

### Key Features

- 🎮 **Real-time Event Detection** - Monitors Elite Dangerous journal files
- 🌈 **Visual Effects System** - Create custom effect sequences with **18 primitive effects**
- 📊 **Visual Topology Editor** - Configure device layouts with rotation support
- 🎨 **Effect Library** - Build and manage reusable lighting effects
- 🎯 **Event Mapping** - Map 239 game events to lighting effects with descriptions
- 🔧 **Device Auto-Detection** - Automatic topology detection (2D/1D/0D)
- 🌐 **Coordinate Normalization** - Device-independent effects with [0,1] coordinate space
- 💾 **Persistent Configuration** - All settings saved automatically
- 🖥️ **Modern Web UI** - Pixel-perfect web interface with offline fonts (Orbitron, Rajdhani)
- ✨ **Interactive Tour Guides** - Step-by-step walkthroughs for all features
- 🌍 **Full i18n Support** - 5 languages (English, Italian, German, Spanish, French)

---

## Quick Start

### Prerequisites

1. **Python 3.11+**
2. **OpenRGB** installed and running ([download](https://openrgb.org/))
3. RGB-capable hardware connected to your PC
4. **Elite Dangerous** (of course!)

### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/ED:Event2Led.git
cd ED:Event2Led

# Install dependencies
pip install -r requirements.txt

# Run application
python src_integrated/main.py
```

### First-Time Setup

1. **Start OpenRGB** with SDK Server enabled (Settings → Enable SDK)
2. **Launch ED:Event2Led**
3. Click **"Reconnect to OpenRGB"** if not auto-connected
4. Navigate to **Device Test** tab to verify devices
5. Go to **Effect Library** tab to create or test effects
6. Go to **Events** tab to map effects to game events
7. Click **"Start Monitoring"** to begin
8. Launch Elite Dangerous and enjoy!

---

## Documentation

### User Guides

- **[Effect Library User Guide](EFFECT_LIBRARY_USER_GUIDE.md)** - Complete guide to creating and using effects
- **[Quick Reference](EFFECT_LIBRARY_QUICK_REFERENCE.md)** - Cheat sheet for common tasks
- **[Journal Events Reference](JOURNAL_EVENTS_REFERENCE.md)** - Elite Dangerous event documentation
- **✨ [NEW UI Quick Start](QUICK_START_NEW_UI.md)** - Try the experimental sidebar UI with violet theme!

### Developer Guides

- **[Effect Library Developer Guide](EFFECT_LIBRARY_DEVELOPER_GUIDE.md)** - Technical implementation details
- **[Integration Guide](INTEGRATION_GUIDE.md)** - How to integrate the system
- **[Unified System README](UNIFIED_SYSTEM_README.md)** - Architecture overview
- **✨ [New UI Implementation](IMPLEMENTATION_SUMMARY.md)** - Sidebar UI MVP architecture and design
- **✨ [New UI Testing](TESTING_NEW_UI.md)** - Testing checklist for sidebar UI

### Additional Documentation

- **[2D Effects Guide](docs/guides/2D_EFFECTS_GUIDE.md)** - Keyboard matrix effects
- **[Unified Effects Guide](docs/guides/UNIFIED_EFFECTS_GUIDE.md)** - Multi-device effects

---

## Features in Detail

### Visual Effects System

Create custom lighting sequences by combining **18 Primitive Effects**:

**Basic Effects:**
1. **Static Transition** - Smooth fade to target color
2. **Breath** - Pulsing between two colors
3. **Color Cycle** - Multi-color wave pattern with 8 directions
4. **Two Color Nuance** - Spatial gradient between two colors
5. **Four Corner Nuance** - Bilinear gradient (2D only)

**Spatial Effects (Topology-Aware):**
6. **Wave** - Directional wave propagation (8 directions)
7. **Bump** - Bidirectional wave with bounce-back
8. **Bloom** - Radial expanding glow from center
9. **Explosion** - Expanding ring with decaying trail (2D only)
10. **Directional Flash** - Quarter-screen flash with direction

**Animated Effects:**
11. **Fire** - Cellular automata fire simulation (bottom→top or top→bottom)
12. **Glitch** - Random LED glitches with persistence
13. **Matrix Rain** - Falling character columns (2D only)
14. **Ocean Waves** - Superimposed sinusoidal waves (2D only)
15. **Plasma** - 2D sinusoid HSV palette cycling (2D only)
16. **Aurora** - Vertical light bands with shimmer (2D only)
17. **Parallax Stars** - Lateral star scroll with depth layers
18. **Lightning** - Discrete lightning strike events (2D only)

**Special:**
- **Keyboard Mapping** - Restore keyboard to saved preset

Each effect is customizable with:
- Colors (RGB 0-255)
- Duration (milliseconds)
- Direction (8-way: cardinal + diagonal directions)
- Loop behavior
- **Normalized coordinates** (device-independent positioning)

### Effect Library Tab

![Effect Library Screenshot]

The main interface for creating Visual Effects:

- **LEFT Panel**: Effect list with action buttons
  - New, Clone, Delete, Import, Export
- **CENTER Panel**: Effect editor
  - Properties (name, description, topology support)
  - Sequence timeline (drag-and-drop steps)
  - Step parameters (dynamic based on effect type)
- **RIGHT Panel**: Testing tools
  - Keyboard matrix simulator (6×22 visual preview)
  - Test buttons (single step, full sequence, hardware)
  - Post-sequence behavior configuration

### Keyboard Matrix Simulator

Real-time visual preview of effects before deploying to hardware:

- 6×22 LED grid representing keyboard layout
- 30+ FPS animation
- Supports both 2D (matrix) and 1D (linear) modes
- No hardware required for testing

### Event Mapping

Map Elite Dangerous events to effects via intuitive UI:

- 60+ game events organized by category
- Support for Fused Effects, Visual Effects, and Color Schemes
- Priority system (0-10, higher interrupts lower)
- Test button for each mapping
- Enable/disable individual mappings

### Device Auto-Detection

Automatic topology detection for all OpenRGB devices:

- **2D (Matrix)**: Keyboards with row/column layout
- **1D (Linear)**: RAM modules, LED strips, mice
- **0D (Single)**: Single-LED devices

Effects automatically adapt to device topology.

---

## New in Phase 1 (March 2026)

### 🌐 Coordinate Normalization System

Transform LED positions from device-specific coordinates to universal [0,1] space:

- **Device-Independent Effects**: Same effect code works on keyboard, mouse, LED strips
- **Multi-Device Effects**: Synchronized effects across multiple devices with shared center point
- **Universal Parameters**: `center_x=0.5` always means "geometric center" regardless of device
- **GlobalBoundingBox**: Unified coordinate system containing all active devices

**Enable in Effect Editor**: Check "Use Normalized Coordinates" for supported effects

### 📐 Topology Editor

Visual device layout configuration with interactive canvas:

- **Drag & Drop**: Position devices in 2D space matching your physical setup
- **Rotation Support**: 0°, 90°, 180°, 270° for horizontal/vertical alignment
- **Real-time Preview**: See bounding box and LED positions while editing
- **JSON Export**: Topology saved to `config/device_topologies.json`

**Access**: Navigate to "Topology Editor" in sidebar

### 📚 Event Definitions System

Complete Elite Dangerous event catalog with descriptions:

- **239 Events**: Extracted from official Journal Manual Excel
- **Tooltips**: Hover over event badges to see full descriptions
- **Visual Badges**: Event associations displayed in Effect Editor panel
- **Quick Reference**: See which events trigger each effect

**Example**: "FSDJump" badge shows "Recorded when jumping from one star system to another"

### 🎯 Directional Parameters

8-way direction control for spatial effects:

- **Cardinal Directions**: Top, Down, Left, Right
- **Diagonal Directions**: Top-Left, Top-Right, Bottom-Left, Bottom-Right
- **Effect-Specific**: Fire supports Bottom→Top and Top→Bottom combustion
- **UI Integration**: Direction selector in Effect Step parameters

### 🎨 Tour Guide System

Interactive UI walkthroughs for new users:

- **Step-by-Step**: Guided tours for Effects Editor, Events Page, Topology Editor
- **Skip/Complete Tracking**: Progress saved per-tour
- **Highlight System**: Focus attention on relevant UI elements
- **Multi-language**: All tours translated to 5 languages

**Activate**: Click "Show Guide" button in navigation sidebar

---

## Screenshots

### Effect Library Editor
```
┌─────────────────────────────────────────────────────────────┐
│  Effect Library Editor                                       │
├───────────┬─────────────────────────┬────────────────────────┤
│           │                         │                        │
│  Effects  │  Sequence Editor        │  Simulator & Test      │
│  List     │                         │                        │
│           │  Name: Hyperspace Jump  │  ┌──────────────────┐ │
│  Visual   │  Desc: FSD jump effect  │  │  [6×22 matrix]   │ │
│  Effects  │                         │  │  [simulator]     │ │
│  └─ Pred  │  Steps:                 │  └──────────────────┘ │
│  └─ Custom│  1. Blue Transition     │                        │
│           │  2. White Explosion     │  ▶ Test Step         │
│  Color    │  3. White Breath        │  ▶ Test Sequence     │
│  Schemes  │                         │  ▶ Test Hardware     │
│           │  [+ Add Step]           │                        │
│  [New]    │                         │  💾 Save             │
│  [Import] │  Step Parameters:       │  📤 Export           │
│  [Export] │  Type: [Explosion ▼]    │                        │
│           │  Colors: [5 colors]     │                        │
│           │  Duration: 1200ms       │                        │
└───────────┴─────────────────────────┴────────────────────────┘
```

### Event Mapper
```
┌─────────────────────────────────────────────────────────────┐
│  Elite Dangerous Event Mappings                             │
├─────────────────────────────────────────────────────────────┤
│  Event          │ Type   │ Effect           │ Pri │ Enabled │
│─────────────────┼────────┼──────────────────┼─────┼─────────│
│  FSDJump        │ Visual │ Hyperspace Jump  │  8  │   ✓     │
│  Docked         │ Visual │ Docked (Safe)    │  5  │   ✓     │
│  UnderAttack    │ Visual │ Combat Alert     │ 10  │   ✓     │
│  ShieldState    │ Fused  │ Shields Down     │ 10  │   ✓     │
│  FuelScoop      │ Visual │ Fuel Scoop       │  3  │   ✓     │
│─────────────────┴────────┴──────────────────┴─────┴─────────│
│  [Save Mappings]  [Test Selected]                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration Files

All configuration is saved automatically to JSON files:

```
config/
├── visual_effects.json       # Visual Effects library
├── color_schemes.json         # Color Schemes library
├── event_mappings.json     # Event-to-effect mappings
└── settings.json              # Application settings
```

You can edit these manually or use the UI (UI recommended).

---

## Project Structure

```
ED:Event2Led/
├── web/                      # Web UI (HTML/CSS/JS with Tailwind)
├── src/                      # Python backend source
│   ├── core/                 # Core logic (effects, rendering, libraries)
│   ├── effects/              # Effect implementations (2D, 1D, spatial)
│   ├── journal/              # Elite Dangerous journal reader
│   └── main.py               # Eel application entry point
├── config/                   # Configuration files (JSON)
├── GameLogs/                 # Sample Elite Dangerous logs
├── tests/                    # Test scripts
└── docs/                     # Documentation (guides, references)
```

---

## Testing

### Automated Tests

```bash
# Test Effect Library core functionality
python src_integrated/test_effect_library.py

# Test GUI Simulator
python src_integrated/test_simulator_gui.py
```

### Manual Testing

1. **Device Test Tab**: Flash/Rainbow/Clear buttons for each device
2. **Effect Library Tab**: Test single steps or full sequences on simulator
3. **Event Mapper Tab**: Test button for each event mapping

---

## Elite Dangerous Events

Commonly mapped events:

| Event | Description | Typical Effect |
|-------|-------------|----------------|
| **FSDJump** | Hyperspace jump | Blue explosion |
| **Docked** | Docked at station | Green transition |
| **UnderAttack** | Taking damage | Red pulse |
| **ShieldState** | Shields down | Red alert |
| **FuelScoop** | Scooping fuel | Orange gradient |
| **FSSDiscoveryScan** | Discovery scanner | Cyan flash |
| **Touchdown** | Landing on planet | Slow fade |
| **Liftoff** | Taking off | Quick sweep |

See [JOURNAL_EVENTS_REFERENCE.md](JOURNAL_EVENTS_REFERENCE.md) for complete list.

---

## Predefined Effects

5 ready-to-use Visual Effects included:

1. **Hyperspace Jump** - Blue transition → White explosion → White breath
2. **Combat Alert** - Continuous red pulse
3. **Docked (Safe)** - Green fade → Green breath
4. **Discovery Flash** - Blue flash → Cyan breath
5. **Rainbow Cycle** - Continuous 6-color wave

Clone and modify these to create custom variations.

---

## Hardware Compatibility

**Tested Devices**:
- ASUS TUF Gaming K7 Keyboard (6×24 matrix)
- Corsair Vengeance RGB RAM (1D linear)
- Various OpenRGB-compatible devices

**Requirements**:
- Device must be supported by OpenRGB
- OpenRGB SDK Server must be enabled

**Check compatibility**: https://openrgb.org/devices

---

## Troubleshooting

### App won't connect to OpenRGB

**Solutions**:
1. Verify OpenRGB is running
2. Enable SDK Server in OpenRGB settings
3. Check firewall isn't blocking localhost:6742
4. Click "Reconnect to OpenRGB" button in app

### Effects not playing on hardware

**Check**:
1. Device is detected (Device Test tab)
2. Effect topology matches device (2D effect needs 2D device)
3. Effect is saved after editing
4. OpenRGB connection is active (green status indicator)

### Simulator not updating

**Solutions**:
1. Click "Stop Test" then try again
2. Restart application
3. Verify effect has valid steps with durations

### Colors look different on hardware vs simulator

**Explanation**:
- Hardware color calibration varies by device
- Adjust in OpenRGB settings, not in effects
- Simulator shows ideal RGB values

---

## Performance

### Benchmarks

- **Simulator FPS**: 30-60 (target: 30)
- **Hardware FPS**: 20-40 (target: 30)
- **Effect Load Time**: ~50ms
- **Library Load Time**: ~200ms
- **Memory Usage**: ~50 MB typical

### Recommendations

- Keep effects under 5 seconds for game events
- Limit concurrent effects to 3-5 devices
- Use simulator for rapid testing to reduce hardware wear

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Follow existing code style (type hints, docstrings)
4. Add tests for new features
5. Update documentation
6. Submit pull request

---

## Technology Stack

- **Python 3.11+**
- **Eel** - Python-to-JavaScript bridge
- **HTML/CSS/JavaScript** - Web UI with Tailwind CSS
- **Built-in OpenRGB SDK client** (`src/utils/openrgb_client.py`) - written from the public protocol description
- **watchdog** - File system monitoring

---

## License

The source code is public, but ED:Event2Led is **source-available, not open source**.
It is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE): you can
read, run, modify and share it for any noncommercial purpose; commercial use is
not allowed. Streaming or recording your gameplay is fine, including on monetized
channels.

- [NOTICE.md](NOTICE.md) — the name and logo, official builds, contributions
- [THIRD-PARTY.md](THIRD-PARTY.md) — licenses of the fonts, icons and libraries used

Official builds: <https://github.com/leandor70/EDEvent2Led/releases>

---

## Acknowledgments

- **OpenRGB Project** - Hardware abstraction layer
- **Elite Dangerous** - By Frontier Developments
- **Eel** - Python-JavaScript bridge
- **Tailwind CSS** - Utility-first CSS framework

---

## Support

- **Documentation**: See guides linked above
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

---

## Roadmap

### Version 2.0 (Current - March 2026)
- ✅ Visual Effects system (18 primitive effects)
- ✅ Effect Library editor
- ✅ Event Mapper v2 with 239 event definitions
- ✅ Color Schemes support
- ✅ **Phase 1.1: Coordinate Normalization** - Device-independent effects
- ✅ **Phase 1.2: Directional Parameters** - 8-way direction control
- ✅ **Topology Editor** - Visual device layout configuration
- ✅ **Topology-Aware LINEAR Effects** - 15 effects migrated to world coordinates
- ✅ **Event Definitions System** - Excel extraction with tooltips
- ✅ **Tour Guide System** - Interactive UI walkthroughs
- ✅ **Offline Font Bundle** - Orbitron + Rajdhani WOFF2
- ✅ **Full i18n** - 5 languages (en, it, de, es, fr)

### Version 2.1 (Planned)
- ⏳ **Phase 2: Enhanced UX** - Parametric center point for radial effects
- ⏳ **Effect Preview Overlay** - Real-time animation preview on topology canvas
- ⏳ Color Scheme visual editor
- ⏳ Effect marketplace/sharing
- ⏳ Animation timeline editor

### Version 3.0 (Future)
- 🔮 3D volumetric effects
- 🔮 Audio reactive effects
- 🔮 Machine learning event prediction
- 🔮 VR headset integration

---

**Happy lighting! o7 Commander**

*Last Updated: 2026-03-24*
*Version: 2.0 - Phase 1 Complete*
