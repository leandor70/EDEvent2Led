# Color Scheme Editor - User Guide

## Overview

The **Color Scheme Editor** allows you to create custom LED-by-LED color configurations for your keyboard. This is perfect for creating static lighting setups that highlight specific keys for Elite Dangerous functions.

---

## Accessing the Editor

1. Launch ED:Event2Led
2. Navigate to **📚 Effect Library** tab
3. Click the **🎯 Color Schemes** sub-tab

---

## Interface Overview

The Color Scheme Editor has 3 panels:

```
┌────────────────────────────────────────────────────────────┐
│  Color Scheme Editor                                        │
├─────────────┬──────────────────────┬───────────────────────┤
│  LEFT       │  CENTER              │  RIGHT                │
│  Schemes    │  LED Editor          │  Color Selection      │
│  List       │                      │  & Tools              │
│             │  [6×22 Matrix]       │                       │
│  └─ ED      │  Click LEDs to       │  [Color Picker]       │
│     Combat  │  assign colors       │  [RGB Spinners]       │
│  └─ ED      │                      │  [Quick Colors]       │
│     Explor  │                      │  [Tools]              │
│  └─ Custom  │                      │  [💾 Save]            │
│             │                      │                       │
│  [New]      │  LED info...         │                       │
│  [Clone]    │                      │                       │
│  [Delete]   │                      │                       │
└─────────────┴──────────────────────┴───────────────────────┘
```

---

## Creating Your First Color Scheme

### Step 1: Create New Scheme

1. Click **"New Scheme"** button (left panel)
2. Enter a name (e.g., "My Combat Layout")
3. Add a description (optional)

### Step 2: Choose a Color

**Option A: Use Quick Colors**
- Click one of the 8 quick color buttons
- Colors available: Red, Green, Blue, Yellow, Cyan, Magenta, White, Black

**Option B: Use RGB Spinners**
- Adjust R (Red): 0-255
- Adjust G (Green): 0-255
- Adjust B (Blue): 0-255

**Option C: Use Color Picker**
- Click "Choose Color..." button
- Select color from system color picker dialog

### Step 3: Assign Colors to LEDs

**Single LED Mode** (default):
1. Click on an LED in the center matrix
2. LED changes to the current color
3. Click another LED to assign the same color

**Paint Mode** (for multiple LEDs):
1. Enable "🖌️ Paint Mode" button
2. Click and drag across multiple LEDs
3. All LEDs under cursor get painted
4. Disable paint mode when done

### Step 4: Save the Scheme

1. Click **"💾 Save Scheme"** button
2. Scheme is saved to library
3. Now available in Events tab for mapping

---

## Predefined Color Schemes

ED:Event2Led includes 3 predefined Elite Dangerous schemes:

### 1. Elite Dangerous - Combat
**Purpose**: Combat-focused key highlighting

**Colors**:
- **Red**: Weapon keys (Primary Fire, Secondary Fire, Deploy Hardpoints)
- **Orange**: Defensive keys (Chaff, Heat Sink, Shield Cell)
- **Blue**: Target management (Target, Subtarget)
- **Green**: Power pips (Weapons, Engines, Systems)

**Key Bindings**: 9 keys mapped

### 2. Elite Dangerous - Exploration
**Purpose**: Exploration and scanning

**Colors**:
- **Cyan**: Scanners (FSS, DSS)
- **Yellow**: Lights and night vision
- **Purple**: Flight assist toggle
- **Green**: Supercruise/jump key

**Key Bindings**: 6 keys mapped

### 3. Elite Dangerous - Trading/Mining
**Purpose**: Trading and mining operations

**Colors**:
- **Green**: Cargo operations (Scoop, Jettison)
- **Orange**: Mining tools (Laser, Limpets)
- **Yellow**: Refinery panel

**Key Bindings**: 6 keys mapped

---

## Advanced Features

### Clone a Scheme

1. Select an existing scheme
2. Click **"Clone"** button
3. Cloned scheme appears with "(Copy)" suffix
4. Modify as needed
5. Save with new name

### Fill All LEDs

1. Choose a color
2. Click **"Fill All LEDs"** button
3. All LEDs set to current color
4. Useful for creating base colors

### Clear All LEDs

1. Click **"Clear All LEDs"** button
2. All LEDs set to black (off)
3. Start fresh with blank slate

### Paint Mode Tips

- Enable for batch coloring multiple keys
- Change color while in paint mode
- Click single LEDs or drag across multiple
- Disable when doing precise single-key work

---

## LED Identification

### Understanding the Matrix

The simulator shows a 6×22 grid representing your keyboard:

```
Row 0: Top row (ESC, F1-F12, etc.)
Row 1: Number row (1-0, -, =)
Row 2: QWERTY row
Row 3: ASDFGH row
Row 4: ZXCVBN row
Row 5: Bottom row (Space, modifiers)
```

**LED Info**:
- Click an LED to see its index
- Format: "LED 45 (Row 2, Col 1)"
- Use this to identify keys for key bindings

---

## Key Bindings (Advanced)

Color schemes support Elite Dangerous key binding references:

**Common Elite Dangerous Keys**:
- `PrimaryFire`
- `SecondaryFire`
- `DeployHardpoints`
- `FireChaffLauncher`
- `UseShieldCell`
- `SelectTarget`
- `HyperSuperCombination`
- `LandingGear`
- `CargoScoop`

**Note**: Key bindings are optional metadata. The visual LED assignments work regardless of bindings.

---

## Importing and Exporting

### Export a Scheme

1. Select scheme in list
2. Click **"Export"** button
3. Choose save location
4. Scheme saved as `.json` file

**Use Cases**:
- Backup your custom schemes
- Share schemes with other users
- Version control your configurations

### Import a Scheme

1. Click **"Import"** button
2. Select `.json` file
3. Scheme added to library
4. Appears in schemes list

**File Format**: Standard JSON (editable in text editor)

---

## Applying Color Schemes

### Method 1: Via Events Tab

1. Go to **🎮 Events** tab
2. Find an event (e.g., "Docked")
3. Set Type: **"Color Scheme"**
4. Select your scheme from dropdown
5. Save mappings

**Result**: When event triggers, color scheme applies to keyboard

### Method 2: Via Hardware Test

**Note**: Direct application coming in future update. Currently use Events tab method.

---

## Tips and Best Practices

### Color Selection

✅ **DO**:
- Use high contrast colors (Red, Green, Blue vs Yellow, Cyan, Magenta)
- Keep related functions in similar colors
- Use color brightness to indicate priority (brighter = more important)

❌ **DON'T**:
- Mix too many colors (stick to 3-5 for clarity)
- Use colors too similar (hard to distinguish)
- Forget about color blindness considerations

### Scheme Organization

**Naming Conventions**:
- `[Game] - [Purpose]` (e.g., "ED - Combat")
- `[Category] - [Variation]` (e.g., "WASD - Gaming")
- Descriptive names help later

**Categories to Consider**:
- Combat layouts
- Exploration layouts
- Trading/mining layouts
- General gaming
- Productivity (non-gaming)

### LED Count

**Typical Keyboard**: 105-110 keys
- **6×24 matrix** = 144 positions (includes gaps)
- Only assign colors to actual keys
- Unassigned LEDs = black (off)

---

## Examples

### Example 1: Simple Combat Layout

**Goal**: Highlight combat keys in red

**Steps**:
1. Create new scheme: "Combat Basics"
2. Select Red color
3. Click these LEDs:
   - Primary fire key
   - Secondary fire key
   - Deploy hardpoints
   - Shield cell
   - Chaff
4. Save scheme

**Result**: 5 red keys for combat

### Example 2: WASD Gaming Layout

**Goal**: Highlight movement keys

**Steps**:
1. Create new scheme: "WASD Movement"
2. Select Cyan color
3. Fill these LEDs:
   - W, A, S, D (movement)
4. Select Yellow color
5. Fill: Space (jump/boost)
6. Save scheme

**Result**: Cyan movement + yellow action key

### Example 3: Elite Dangerous Full Layout

**Goal**: Complete ED key layout

**Steps**:
1. Clone "ED - Combat" scheme
2. Rename to "My ED Complete"
3. Add exploration keys (cyan):
   - FSS, DSS, Scanners
4. Add flight keys (green):
   - Flight assist, Landing gear
5. Add utility keys (orange):
   - Lights, Cargo scoop
6. Save scheme

**Result**: Comprehensive 20+ key layout

---

## Troubleshooting

### Colors Don't Match on Hardware

**Problem**: Simulator colors differ from keyboard

**Explanation**:
- This is normal due to device color calibration
- Each keyboard has unique color reproduction
- OpenRGB can adjust calibration

**Fix**:
1. Open OpenRGB
2. Select your device
3. Adjust color calibration settings
4. Test until colors match expectations

### LED Positions Don't Match Keyboard

**Problem**: LED grid doesn't match physical keyboard layout

**Explanation**:
- The 6×22 grid is a standard representation
- Your keyboard may have different physical layout
- LED indices still map correctly to keys

**Solution**:
- Use trial-and-error to identify LED positions
- Click an LED, note the index
- Test on hardware to verify key
- Create a reference map for your keyboard

### Scheme Not Applying

**Problem**: Saved scheme doesn't apply when event triggers

**Check**:
1. Scheme is saved (click Save button)
2. Event mapping points to correct scheme
3. Event mapping Type is "Color Scheme"
4. Mapping is enabled (checkbox)
5. OpenRGB is connected

### Can't Delete Predefined Schemes

**Explanation**: Predefined schemes (ED Combat, ED Exploration, ED Trading) are protected

**Workaround**: Clone the scheme, modify the clone, and hide the original

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New Scheme | Ctrl+N |
| Save Scheme | Ctrl+S |
| Clone Scheme | Ctrl+D |
| Toggle Paint Mode | P |
| Clear All | Ctrl+Delete |

*(Note: Shortcuts may vary by OS)*

---

## File Locations

**Color Schemes Library**: `config/color_schemes.json`

**Exported Schemes**: User-chosen location

**Format**: JSON (human-readable)

---

## Integration with Visual Effects

**Combining Color Schemes and Visual Effects**:

1. **Static Background**: Use Color Scheme as base lighting
2. **Dynamic Overlay**: Visual Effects play on top temporarily
3. **Return to Base**: After effect ends, Color Scheme remains

**Example Workflow**:
1. Apply "ED - Combat" Color Scheme (static)
2. "UnderAttack" event triggers → Combat Alert Visual Effect plays
3. Effect ends → Returns to Combat Color Scheme

**Post-Sequence Behavior**:
- Visual Effects can specify "Apply Color Scheme" as post-behavior
- This applies a Color Scheme after effect sequence completes

---

## Advanced: Manual JSON Editing

Color Scheme JSON format:

```json
{
  "id": "my_scheme",
  "name": "My Custom Scheme",
  "description": "Description here",
  "device_type": "keyboard",
  "led_colors": {
    "0": [255, 0, 0],     // LED 0 = Red
    "1": [0, 255, 0],     // LED 1 = Green
    "2": [0, 0, 255]      // LED 2 = Blue
  },
  "key_bindings": {
    "PrimaryFire": 0,
    "SecondaryFire": 1,
    "Boost": 2
  },
  "metadata": {
    "author": "You",
    "category": "Custom",
    "version": "1.0"
  }
}
```

**Fields**:
- `id`: Unique identifier (use underscores, no spaces)
- `led_colors`: Map of LED index → RGB array
- `key_bindings`: Optional ED key name → LED index
- `metadata`: Optional extra information

---

## Future Features (Roadmap)

⏳ Planned enhancements:

- **Key Templates**: Pre-made layouts for common keyboards
- **Visual Key Picker**: Click actual key images instead of grid
- **Gradient Fill**: Auto-generate color gradients across key ranges
- **Layers**: Multiple color layers with blending modes
- **Animations**: Pulsing or breathing on specific keys
- **Import from OpenRGB**: Import existing OpenRGB profiles

---

## Need Help?

- **User Guide**: This document
- **Developer Guide**: `EFFECT_LIBRARY_DEVELOPER_GUIDE.md`
- **Quick Reference**: `EFFECT_LIBRARY_QUICK_REFERENCE.md`
- **GitHub Issues**: Report bugs or request features

---

**Happy Coloring! 🎨**

---

*Last Updated: 2025-12-18*
*ED:Event2Led Version: 2.0*
