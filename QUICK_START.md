# ED:Event2Led — Quick Start

## Prerequisites

1. **Python 3.11+** on Windows
2. **OpenRGB** installed and running with SDK Server enabled (`localhost:6742`)
3. **Elite Dangerous** (optional for initial setup)

## Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the App

```bat
start_dev_server.bat
```

The browser opens automatically at `http://localhost:8000`. The app starts an Eel server on port 8000.

> **OpenRGB not running?** Start OpenRGB after the app — the next hardware operation will auto-connect.

---

## First Steps

### 1. Configure your hardware (Keyboard Designer)

1. Open **Keyboard Designer** from the sidebar
2. Click **Load Keybindings** to auto-detect your Elite Dangerous `.binds` file — keys are colored by function category (flight, combat, navigation…)
3. Click individual keys to assign custom colors
4. Click **P1** → **SAVE PRESET** to store your configuration
5. Repeat for P2 and P3 if you want multiple profiles

### 2. Map game events to effects (Events page)

1. Open the **Events** page
2. Browse 239 Elite Dangerous events (filtered by category: Travel, Combat, Exploration…)
3. Click **+ Assign** on any event and select an effect from the gallery
4. Click **Save Mappings**

### 3. Start monitoring (Home page)

1. Open the **Home** page (index.html)
2. Click **Start Monitoring** — the app begins watching your Elite Dangerous journal directory
3. Play the game — events trigger RGB effects in real time

### 4. Monitor game state (Game Status page)

The **Game Status** page shows live ship parameters (overheating, shields, interdiction, etc.) updated every 750ms from `Status.json`.

---

## Key Pages

| Page | URL | Purpose |
|---|---|---|
| Home | `/index.html` | Monitoring control, connection status |
| Effects Editor | `/effects-editor.html` | Create/edit multi-step lighting sequences |
| Events | `/events.html` | Map ED events to effects |
| Keyboard Designer | `/keyboard-designer.html` | Per-LED color presets |
| Game Status | `/status.html` | Real-time ship parameters |
| Test | `/test.html` | Hardware test and diagnostics |
| Log | `/log.html` | Activity log |
| Configuration | `/code.html` | OpenRGB host/port, journal path |

---

## Configuration Files

Located in `config/`:

| File | Purpose |
|---|---|
| `settings.json` | OpenRGB connection, journal path |
| `visual_effects.json` | Your saved lighting effects |
| `event_mappings.json` | Event→effect assignments |
| `keyboard_presets.json` | Keyboard color presets P1/P2/P3 |
| `color_schemes.json` | Color scheme library |
