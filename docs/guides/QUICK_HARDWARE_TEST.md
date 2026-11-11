# Quick Hardware Test Guide

**Fast track to testing the Effect Library with your RGB devices**

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **OpenRGB installed** - Download from https://openrgb.org/
- [ ] **RGB devices connected** - Keyboard, RAM, mouse, etc.
- [ ] **Python 3.11+** with all dependencies installed
- [ ] **ED:Event2Led repository** cloned and set up

---

## Step 1: Start OpenRGB (2 minutes)

### A. Launch OpenRGB

1. Open OpenRGB application
2. Wait for device detection to complete
3. Verify your devices appear in the device list

### B. Enable SDK Server

1. Click **Settings** (gear icon)
2. In "SDK Server" section:
   - ✅ Check **"Start Server"**
   - ✅ Check **"Start at Launch"** (optional, but recommended)
3. Click **Save**
4. **Restart OpenRGB** (close and reopen)

### C. Verify SDK Server is Running

Look for:
- Status indicator showing "SDK Server: Running" or similar
- Port 6742 is listening

**Quick Test**:
```bash
telnet localhost 6742
```
If it connects, SDK Server is working! (Press Ctrl+C to exit)

---

## Step 2: Run Hardware Integration Test (5 minutes)

### A. Open Terminal

```bash
cd d:\Lavori\Claude\ED:Event2Led\src_integrated
python test_hardware_integration.py
```

### B. Follow Interactive Prompts

The test will:

1. **Connect to OpenRGB** ✅
   - Shows detected devices
   - Lists device topology (2D/1D/0D)

2. **Test Simple Flash** 💡
   - Press ENTER when prompted
   - All devices flash WHITE for 2 seconds
   - Verifies basic hardware control

3. **Test Visual Effect** 🎨
   - Choose an effect (or press ENTER for Hyperspace Jump)
   - Effect plays on all compatible devices
   - Watch your RGB hardware!

4. **Test All Effects** (Optional) 🌈
   - Type 'y' to test all predefined effects sequentially
   - Each effect plays for 3 seconds
   - Great for seeing the full library in action

5. **Test Color Scheme** (Optional) 🎯
   - Type 'y' to apply a color scheme
   - Static LED-by-LED colors (for keyboards)

6. **Performance Test** (Optional) ⚡
   - Type 'y' to test rapid effect switching
   - Measures system responsiveness

### C. Expected Output

```
======================================================================
Effect Library - Hardware Integration Test
======================================================================

[TEST 1] Connecting to OpenRGB...
✅ Connected to OpenRGB
  Server: localhost:6742
  Devices detected: 3

[TEST 2] Initializing UnifiedEffectManager...
✅ UnifiedEffectManager initialized
  Total devices: 3

=== Device Summary ===
  2D Matrix: 1
  1D Linear: 2
  Total: 3

  Device Details:
  1. ASUS TUF Gaming K7
     Type: Keyboard
     Topology: MATRIX
     LEDs: 105
     Dimensions: 6×24

  2. Corsair Vengeance RGB
     Type: DRAM
     Topology: LINEAR
     LEDs: 10

  3. Corsair Vengeance RGB
     Type: DRAM
     Topology: LINEAR
     LEDs: 10

[TEST 3] Loading Visual Effect Library...
✅ Library loaded: 5 effects available
  - Hyperspace Jump (hyperspace_jump)
    Steps: 3, Duration: 3700ms
  - Combat Alert (combat_alert)
    Steps: 1, Duration: 0ms
  - Docked (Safe) (docked_safe)
    Steps: 2, Duration: 2500ms
  - Discovery Flash (discovery_flash)
    Steps: 2, Duration: 2500ms
  - Rainbow Cycle (rainbow_cycle)
    Steps: 1, Duration: 0ms

[TEST 4] Testing simple effect on hardware...
  This will flash all devices WHITE for 2 seconds
  Press ENTER to continue...
  Setting all LEDs to WHITE...
  Clearing all LEDs...
✅ Simple test completed

[TEST 5] Testing Visual Effect on hardware...
  Available effects:
  1. Hyperspace Jump
  2. Combat Alert
  3. Docked (Safe)
  4. Discovery Flash
  5. Rainbow Cycle

  Enter effect number (or ENTER for Hyperspace Jump):

  Testing 'Hyperspace Jump' on all devices...
  Steps: 3
  Duration: 3700ms
  Topology support: 2D, 1D
  ✓ Compatible: ASUS TUF Gaming K7
  ✓ Compatible: Corsair Vengeance RGB
  ✓ Compatible: Corsair Vengeance RGB

  Playing on 3 compatible device(s)...
✅ Visual Effect test completed

...

======================================================================
Hardware Integration Test Complete!
======================================================================

✅ Tests Passed:
  1. OpenRGB connection
  2. UnifiedEffectManager initialization
  3. Visual Effect Library loading
  4. Simple hardware control
  5. Visual Effect playback
  6. Multi-effect sequencing
  7. Color Scheme application
  8. Performance testing

🎉 Effect Library is ready for production use!
```

---

## Step 3: Test in Main Application (10 minutes)

### A. Launch ED:Event2Led

```bash
cd d:\Lavori\Claude\ED:Event2Led\src_integrated
python main.py
```

### B. Test Device Tab

1. Go to **"🔍 Device Test"** tab
2. Verify all your devices are listed
3. Click **"⚡ Flash"** on each device to identify them
4. Click **"🌈 Rainbow"** to test animation
5. Click **"⬛ Clear"** to turn off

### C. Test Effect Library Tab

1. Go to **"📚 Effect Library"** tab
2. Select a predefined effect (e.g., "Hyperspace Jump")
3. Click **"▶ Test on Hardware"**
4. Watch effect play on your devices!

### D. Create Custom Effect

1. In Effect Library tab, click **"New Effect"**
2. Set name: "My Test Effect"
3. Click **"+ Add Step"**
4. Configure:
   - Type: Static Transition
   - Color: Red (255, 0, 0)
   - Duration: 1000ms
5. Click **"💾 Save"**
6. Click **"▶ Test on Hardware"**
7. See your custom effect!

### E. Map to Game Event

1. Go to **"🎮 Events"** tab
2. Find event "FSDJump"
3. Set Type: **"Visual"**
4. Select Effect: **"Hyperspace Jump"**
5. Set Priority: **8**
6. Check **"Enabled"**
7. Click **"Save Mappings"**
8. Click **"Test Selected"** to preview

---

## Step 4: Test with Elite Dangerous (5 minutes)

### A. Configure Monitoring

1. In ED:Event2Led, verify Event Mappings are saved
2. Click **"▶️ Start Monitoring"**
3. Status should show "Monitoring active"

### B. Launch Elite Dangerous

1. Start the game
2. Load into game (any mode - main game, Horizons, Odyssey)
3. Perform actions that trigger events:
   - **FSD Jump** → Should see Hyperspace Jump effect
   - **Dock at station** → Should see Docked effect
   - **Get attacked** → Should see Combat Alert effect

### C. Verify Effects Trigger

Watch your RGB devices:
- Effects should trigger automatically when events occur
- Higher priority effects interrupt lower priority
- Effects play completely before clearing

---

## Troubleshooting

### OpenRGB Connection Issues

**Problem**: `TimeoutError: timed out`

**Fix**:
1. Verify OpenRGB is running (check taskbar/system tray)
2. Go to OpenRGB Settings → Verify "Start Server" is checked
3. Restart OpenRGB
4. Try test again

### Devices Not Detected

**Problem**: Test shows 0 devices

**Fix**:
1. In OpenRGB: Tools → Rescan Devices
2. Check device compatibility: https://openrgb.org/devices
3. Update OpenRGB to latest version
4. Replug USB devices

### Effects Don't Play

**Problem**: Effect test succeeds but no visual change

**Fix**:
1. Check device isn't in "Direct" mode (use "Software" mode in OpenRGB)
2. Verify effect topology matches device (see device summary)
3. Test with simple white flash first
4. Check device isn't controlled by another app

### Colors Look Wrong

**Problem**: Colors on hardware differ from simulator

**Explanation**:
- This is normal! Each device has different color calibration
- You can adjust in OpenRGB settings (not in ED:Event2Led)
- Use OpenRGB's calibration tools

---

## Quick Reference Commands

### Test Hardware Integration
```bash
cd src_integrated
python test_hardware_integration.py
```

### Test Simulator Only (No Hardware)
```bash
cd src_integrated
python test_simulator_gui.py
```

### Test Core Library (No GUI)
```bash
cd src_integrated
python test_effect_library.py
```

### Launch Main Application
```bash
cd src_integrated
python main.py
```

---

## Success Criteria

You've successfully tested the hardware when:

- ✅ OpenRGB connects (no timeout errors)
- ✅ All devices detected with correct topology
- ✅ White flash test works on all devices
- ✅ At least one Visual Effect plays correctly
- ✅ Effects visible on physical RGB devices
- ✅ Simulator preview matches hardware (approximately)
- ✅ Event mapping test triggers effects

---

## Next Steps After Successful Test

1. **Create Custom Effects**
   - Experiment with different base effects
   - Adjust colors for your preference
   - Build effect sequences

2. **Configure Event Mappings**
   - Map your favorite events
   - Set appropriate priorities
   - Test each mapping

3. **Optimize Settings**
   - Adjust effect durations
   - Choose per-device effects if desired
   - Fine-tune colors

4. **Play Elite Dangerous!**
   - Start monitoring
   - Enjoy synchronized RGB lighting
   - Share your setup with others

---

## Getting Help

If you encounter issues:

1. Check **HARDWARE_TEST_REPORT.md** for detailed troubleshooting
2. Review **EFFECT_LIBRARY_USER_GUIDE.md** for usage help
3. Check OpenRGB logs for device-specific issues
4. Verify Elite Dangerous journal files are being created

---

**Total Test Time**: ~20 minutes
**Difficulty**: Beginner-friendly
**Result**: Fully functional RGB lighting system!

🎉 **Enjoy your synchronized Elite Dangerous RGB experience!** 🎉
