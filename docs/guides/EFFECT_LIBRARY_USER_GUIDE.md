# Effect Library - User Guide

## Overview

The **Effect Library** is the central system for creating, managing, and testing RGB lighting effects in ED:Event2Led. It allows you to build custom lighting sequences by combining **Base Effects** with different colors, durations, and parameters.

---

## Table of Contents

1. [Key Concepts](#key-concepts)
2. [Getting Started](#getting-started)
3. [Base Effects Reference](#base-effects-reference)
4. [Creating Visual Effects](#creating-visual-effects)
5. [Testing Effects](#testing-effects)
6. [Mapping to Game Events](#mapping-to-game-events)
7. [Import/Export](#importexport)
8. [Tips and Best Practices](#tips-and-best-practices)

---

## Key Concepts

### Visual Effects
A **Visual Effect** is an ordered sequence of one or more **Base Effects** that play sequentially on your RGB devices. Think of it like a playlist of lighting animations.

**Example**: A "Hyperspace Jump" effect might consist of:
1. Blue fade-in (500ms)
2. White explosion (1200ms)
3. White breathing effect (2000ms)

### Base Effects
**Base Effects** are the atomic building blocks - fundamental lighting animations with customizable parameters:
- **Colors**: RGB values (0-255 for each channel)
- **Duration**: How long the effect plays (in milliseconds)
- **Direction**: For spatial effects (horizontal, vertical, diagonal)
- **Loops**: Some effects can loop infinitely

### Device Topologies
RGB devices have different layouts:
- **2D (Matrix)**: Keyboards with rows and columns (e.g., 6×22 keys)
- **1D (Linear)**: LED strips, RAM modules (single row of LEDs)
- **0D (Single)**: Devices with one LED (rare)

Each Visual Effect declares which topologies it supports.

---

## Getting Started

### Opening the Effect Library

1. Launch ED:Event2Led
2. Click the **📚 Effect Library** tab
3. The interface has 3 panels:
   - **LEFT**: List of effects with action buttons
   - **CENTER**: Effect editor (properties, sequence, parameters)
   - **RIGHT**: Visual simulator and test controls

### Your First Effect

Let's create a simple "Red Alert" effect:

1. **Click "New Effect"** in the left panel
2. **Fill in properties**:
   - Name: `Red Alert`
   - Description: `Pulsing red warning light`
   - Topology Support: Check `2D`, `1D`, `0D`
3. **Add a step**:
   - Click **"+ Add Step"**
   - Select effect type: **Breath**
   - Color 1: Red (255, 0, 0)
   - Color 2: Dark Red (128, 0, 0)
   - Duration: 1000ms
4. **Test on simulator**:
   - Click **"▶ Test Full Sequence"**
   - Watch the preview on the keyboard simulator
5. **Save**:
   - Click **"💾 Save"**

---

## Base Effects Reference

### 1. Static Transition (Fade)

**Description**: Smoothly transitions from current color to target color.

**Parameters**:
- **Color**: Target RGB color
- **Duration**: Fade duration in milliseconds

**Use Cases**:
- Scene transitions
- Gentle color changes
- Intro/outro effects

**Example**:
```
Type: Static Transition
Color: Blue (0, 0, 255)
Duration: 500ms
→ Fades from black to blue over 0.5 seconds
```

---

### 2. Breath (Pulse)

**Description**: Oscillates smoothly between two colors, creating a breathing effect.

**Parameters**:
- **Color 1**: First color (bright state)
- **Color 2**: Second color (dim state)
- **Duration**: Full breath cycle duration
- **Loop Infinite**: If enabled, breathes continuously

**Use Cases**:
- Idle/ambient effects
- Pulsing alerts
- Smooth color transitions

**Example**:
```
Type: Breath
Color 1: White (255, 255, 255)
Color 2: Black (0, 0, 0)
Duration: 2000ms
Loop Infinite: Yes
→ Smooth white pulse every 2 seconds, repeating forever
```

---

### 3. Color Cycle (Wave)

**Description**: Cycles through multiple colors in a wave pattern moving across the device.

**Parameters**:
- **Colors**: List of 2+ RGB colors
- **Direction**: `left`, `right`, `up`, `down`, `tl`, `tr`, `bl`, `br`
- **Duration**: Time for one complete cycle
- **Loop Infinite**: If enabled, cycles continuously

**Use Cases**:
- Rainbow effects
- Multi-color waves
- Dynamic ambient lighting

**Example**:
```
Type: Color Cycle
Colors: [Red, Orange, Yellow, Green, Blue, Purple]
Direction: right
Duration: 3000ms
Loop Infinite: Yes
→ Rainbow wave moving from left to right, repeating
```

**Supported Directions** (2D devices):
- `left` / `right`: Horizontal sweep
- `up` / `down`: Vertical sweep
- `tl` / `tr` / `bl` / `br`: Diagonal from top-left/top-right/bottom-left/bottom-right

---

### 4. Two Color Nuance (Gradient)

**Description**: Creates a smooth spatial gradient between two colors across the device.

**Parameters**:
- **Color 1**: Start color
- **Color 2**: End color
- **Direction**: Gradient orientation
- **Duration**: Display duration (static gradient)

**Use Cases**:
- Atmospheric effects
- Scene setting
- Dual-color themes

**Example**:
```
Type: Two Color Nuance
Color 1: Blue (0, 0, 255)
Color 2: Cyan (0, 255, 255)
Direction: vertical
Duration: 2000ms
→ Blue at top gradually transitions to cyan at bottom
```

**Note**: For 1D devices, only `horizontal` direction is meaningful.

---

### 5. Four Corner Nuance (Corner Gradient)

**Description**: Creates a bilinear gradient with different colors at each corner. **2D devices only.**

**Parameters**:
- **Color 1**: Top-left corner
- **Color 2**: Top-right corner
- **Color 3**: Bottom-right corner
- **Color 4**: Bottom-left corner
- **Duration**: Display duration

**Use Cases**:
- Complex atmospheric effects
- Spatial depth
- Multi-zone themes

**Example**:
```
Type: Four Corner Nuance
Color 1 (TL): Red (255, 0, 0)
Color 2 (TR): Yellow (255, 255, 0)
Color 3 (BR): Green (0, 255, 0)
Color 4 (BL): Blue (0, 0, 255)
Duration: 3000ms
→ Complex color gradient with all four corners different
```

**Fallback**: On 1D devices, uses only Color 1 and Color 3 as a simple gradient.

---

### 6. Explosion (Ripple)

**Description**: Concentric circles expanding outward from center. **2D devices only.**

**Parameters**:
- **Colors**: 5 colors defining the ripple gradient (inner to outer)
- **Duration**: Time for ripple to expand completely
- **Num Loops**: How many ripples to create
- **Loop Infinite**: If enabled, creates continuous ripples

**Use Cases**:
- Impact effects
- Hyperspace jumps
- Attention-grabbing alerts

**Example**:
```
Type: Explosion
Colors: [
  Deep Blue (0, 50, 255),
  Blue (0, 150, 255),
  Light Blue (100, 200, 255),
  Pale Blue (200, 220, 255),
  White (255, 255, 255)
]
Duration: 1200ms
Num Loops: 1
→ Single ripple expanding from center, dark blue to white
```

**Fallback**: On 1D devices, creates a center-out wave effect.

---

## Creating Visual Effects

### Step-by-Step Process

#### 1. Create New Effect

Click **"New Effect"** in the left panel. A blank effect is created with default properties.

#### 2. Set Properties

In the **CENTER** panel, configure:

- **Name**: Descriptive name (e.g., "FSD Jump", "Combat Alert")
- **Description**: What the effect represents
- **Topology Support**: Which device types this effect works with
  - Check `2D` for keyboards
  - Check `1D` for LED strips, RAM
  - Check `0D` for single-LED devices

**Tip**: Most effects should support both 2D and 1D for maximum compatibility.

#### 3. Add Steps

Click **"+ Add Step"** to add a base effect to the sequence.

For each step, configure:
- **Effect Type**: Choose from 6 base effects
- **Parameters**: Colors, duration, direction (varies by type)
- **Loop Infinite**: Whether this step repeats forever

**Order matters**: Steps play sequentially from top to bottom.

#### 4. Reorder Steps (if needed)

Select a step and use:
- **↑ Up**: Move step earlier in sequence
- **↓ Down**: Move step later in sequence

#### 5. Configure Post-Sequence Behavior

After all steps finish, choose what happens:

- **Turn Off**: All LEDs go black (default)
- **Static Color**: Hold a specific color
- **Loop Effect**: Repeat a specific step number continuously
- **Color Scheme**: Apply a saved keyboard color scheme

#### 6. Test the Effect

Use the **RIGHT** panel test buttons:

- **▶ Test Single Step**: Preview just the selected step
- **▶ Test Full Sequence**: Preview entire effect on simulator
- **▶ Test on Hardware**: Play on actual RGB devices

#### 7. Save

Click **💾 Save** to store the effect in the library.

---

## Testing Effects

### Simulator Testing

The **Keyboard Matrix Simulator** shows a visual preview without requiring actual hardware.

**Benefits**:
- Fast iteration (30+ FPS)
- See effects before deployment
- No hardware wear from testing
- Works without OpenRGB

**To test on simulator**:
1. Select or create an effect
2. Click **"▶ Test Full Sequence"**
3. Watch the simulator in the RIGHT panel
4. Click **"⏹ Stop Test"** to stop

**Simulator Colors**: The grid shows RGB colors in real-time, simulating your keyboard layout.

### Hardware Testing

**Prerequisites**:
- OpenRGB running with SDK Server enabled
- RGB devices connected and detected

**To test on hardware**:
1. Ensure devices are connected (check status indicator)
2. Select an effect
3. Click **"▶ Test on Hardware"**
4. Effect plays on all compatible devices
5. Dialog shows how many devices are playing

**Device Compatibility**: Effects only play on devices matching the topology support. For example:
- Effect supports `2D` → plays on keyboards
- Effect supports `1D` → plays on RAM, LED strips
- Effect supports `0D` → plays on single-LED devices

---

## Mapping to Game Events

Once you've created Visual Effects, map them to Elite Dangerous events:

### Step-by-Step

1. **Go to "🎮 Events" tab**
2. **Find the game event** (e.g., "FSDJump", "Docked", "UnderAttack")
3. **Set "Type" dropdown** to **"Visual"**
4. **Select your effect** from the "Effect" dropdown
5. **Set Priority** (0-10, higher = more important)
6. **Enable** the mapping with the checkbox
7. **Click "Save Mappings"**

### Testing Event Mappings

Click **"Test Selected"** to preview how the effect will look when the game event triggers.

### Priority System

When multiple events occur simultaneously, higher priority effects take precedence:

- **10**: Critical (shields down, death)
- **8**: Important (FSD jump, combat)
- **5**: Normal (docking, trading)
- **3**: Low (fuel scoop, scanning)
- **0**: Ambient

---

## Import/Export

### Exporting Effects

Share effects with other users or back up your creations:

1. Select an effect in the left panel
2. Click **"Export"**
3. Choose save location
4. Effect saved as `.json` file

### Importing Effects

Add effects from other users or restore backups:

1. Click **"Import"**
2. Select `.json` effect file
3. Effect added to library
4. Verify and save

### Effect File Format

Effects are stored in `config/visual_effects.json` as JSON. You can edit manually if needed (see Developer Guide for format details).

---

## Tips and Best Practices

### Effect Design

✅ **DO**:
- Keep effects under 5 seconds for game events (longer feels unresponsive)
- Use 2-3 steps maximum for simple, clear effects
- Test on simulator first before hardware
- Name effects descriptively ("FSD Jump Blue", not "Effect1")
- Support both 2D and 1D when possible

❌ **DON'T**:
- Create extremely long effects (10+ seconds) - game events will queue up
- Use too many steps (5+) - becomes complex and hard to maintain
- Use `loop_infinite=true` in middle steps (sequence never advances)
- Forget to test on actual hardware before mapping to events

### Color Choices

**Elite Dangerous Themes**:
- **Hyperspace**: Blues and whites (0, 0, 255) → (255, 255, 255)
- **Combat**: Reds and oranges (255, 0, 0) → (255, 128, 0)
- **Docked**: Greens (0, 255, 0)
- **Shields Down**: Pulsing red (255, 0, 0)
- **Discovery**: Bright blues and cyan (0, 200, 255)
- **Fuel Scoop**: Orange to yellow (255, 128, 0) → (255, 255, 0)

### Performance

- **Simulator**: Can handle any complexity
- **Hardware**: Keep effects under 5 steps for smooth playback
- **Duration**: 500-3000ms per step is ideal
- **Colors**: No performance impact from color choices

### Organization

Create categories by naming convention:
- `[Combat] Shield Alert`
- `[Travel] FSD Jump`
- `[Station] Docked`
- `[Discovery] Scan Complete`

This makes effects easy to find in the dropdown lists.

---

## Predefined Effects

ED:Event2Led includes 5 ready-to-use effects:

### 1. Hyperspace Jump
**Steps**: Blue transition → White explosion → White breath
**Duration**: ~3.7 seconds
**Use**: FSD jumps

### 2. Combat Alert
**Steps**: Red pulse (infinite)
**Duration**: Continuous
**Use**: UnderAttack, HullDamage

### 3. Docked (Safe)
**Steps**: Green fade → Green breath
**Duration**: ~2.5 seconds
**Use**: Docked event

### 4. Discovery Flash
**Steps**: Blue flash → Cyan breath
**Duration**: ~2.5 seconds
**Use**: Scan, FSSDiscoveryScan

### 5. Rainbow Cycle
**Steps**: 6-color wave (infinite)
**Duration**: Continuous
**Use**: Ambient/idle mode

These can be used as-is or cloned and modified to create variations.

---

## Troubleshooting

### "Effect not playing on hardware"

**Check**:
1. OpenRGB is running (status indicator should show green)
2. Device topology matches effect support (2D effect won't play on 1D device)
3. Effect is saved (click 💾 Save after editing)
4. Device is detected (check Device Test tab)

### "Simulator not updating"

**Solutions**:
1. Click "⏹ Stop Test" then try again
2. Restart application
3. Check effect has valid steps with colors and durations

### "Effect plays too fast/slow"

**Adjust**:
- Step durations (duration_ms parameter)
- Total sequence should be 2-5 seconds for game events

### "Colors look wrong"

**Verify**:
- RGB values are 0-255 (not 0.0-1.0)
- Simulator shows colors correctly (if hardware differs, check OpenRGB calibration)
- Test on both simulator and hardware

---

## Need Help?

- **User Guide**: This document
- **Developer Guide**: `EFFECT_LIBRARY_DEVELOPER_GUIDE.md`
- **Event Reference**: `JOURNAL_EVENTS_REFERENCE.md`
- **GitHub Issues**: [Report bugs or request features](https://github.com/your-repo/issues)

---

**Happy Lighting! 🌈**

---

*Last Updated: 2025-12-18*
*ED:Event2Led Version: 2.0*
