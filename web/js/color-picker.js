/**
 * color-picker.js — Reusable HSV Color Picker Modal
 *
 * Drop-in for any page: include this script and call window.openColorPicker().
 * The modal HTML is injected automatically into document.body on first load.
 *
 * Public API:
 *   openColorPicker(initialHex, callback)
 *     initialHex  — e.g. '#FF6600' (default if omitted)
 *     callback    — function(hex) called when user clicks Confirm
 *
 * Example:
 *   openColorPicker('#00AAFF', color => console.log(color));
 */

(function () {
    // ── Inject modal HTML ────────────────────────────────────────
    const _tpl = document.createElement('div');
    _tpl.innerHTML = `
<div id="colorPickerModal" style="
    display:none; position:fixed; top:0; left:0; right:0; bottom:0;
    background:rgba(0,0,0,0.8); z-index:10100;
    align-items:center; justify-content:center;">
  <div style="
      background:#0a0a0a;
      border:2px solid var(--primary-accent,#FF6600);
      border-radius:12px; padding:24px; width:480px; max-width:90vw;">

    <!-- Header -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <h3 style="color:var(--primary-accent,#FF6600); font-size:16px; font-weight:bold; text-transform:uppercase; font-family:'Rajdhani',sans-serif; letter-spacing:0.15em;">
        Color Picker
      </h3>
      <button id="colorPickerClose" style="background:none; border:none; color:rgba(255,255,255,0.5); font-size:24px; cursor:pointer; width:32px; height:32px; padding:0; line-height:1;">×</button>
    </div>

    <!-- Wheel + Preview row -->
    <div style="display:flex; gap:16px; margin-bottom:20px; align-items:flex-start;">
      <div style="position:relative; flex-shrink:0;">
        <canvas id="colorWheelCanvas" width="180" height="180" style="
            display:block; cursor:crosshair; border-radius:50%;
            border:2px solid rgba(255,102,0,0.4);"></canvas>
        <div id="colorWheelCursor" style="
            position:absolute; width:12px; height:12px;
            border:2px solid white; border-radius:50%;
            box-shadow:0 0 4px rgba(0,0,0,0.8);
            transform:translate(-50%,-50%); pointer-events:none;
            top:50%; left:50%;"></div>
      </div>
      <div style="flex:1; display:flex; flex-direction:column; gap:12px;">
        <div id="colorPreview" style="
            width:100%; height:56px;
            border:2px solid var(--primary-accent,#FF6600);
            border-radius:8px; background:#FF6600;"></div>
        <div>
          <label style="color:rgba(255,255,255,0.7); font-size:11px; display:block; margin-bottom:4px; text-transform:uppercase; font-family:'Rajdhani',sans-serif;">HEX</label>
          <input type="text" id="colorHexInput" value="#FF6600" style="
              width:100%; background:rgba(0,0,0,0.6);
              border:1px solid rgba(255,255,255,0.1); color:white;
              padding:8px 10px; border-radius:6px; font-size:13px;
              font-family:monospace; box-sizing:border-box;">
        </div>
        <div>
          <label style="color:rgba(255,255,255,0.7); font-size:11px; display:block; margin-bottom:4px; text-transform:uppercase; font-family:'Rajdhani',sans-serif;">
            Brightness: <span id="colorVValue">100</span>%
          </label>
          <input type="range" id="colorVSlider" min="0" max="100" value="100" style="width:100%;">
        </div>
      </div>
    </div>

    <!-- RGB sliders -->
    <div style="margin-bottom:20px;">
      <div style="margin-bottom:8px;">
        <label style="color:#ef4444; font-size:12px; display:block; margin-bottom:4px; font-family:'Rajdhani',sans-serif;">Red: <span id="colorRValue">255</span></label>
        <input type="range" id="colorRSlider" min="0" max="255" value="255" style="width:100%;">
      </div>
      <div style="margin-bottom:8px;">
        <label style="color:#10b981; font-size:12px; display:block; margin-bottom:4px; font-family:'Rajdhani',sans-serif;">Green: <span id="colorGValue">102</span></label>
        <input type="range" id="colorGSlider" min="0" max="255" value="102" style="width:100%;">
      </div>
      <div style="margin-bottom:8px;">
        <label style="color:#3b82f6; font-size:12px; display:block; margin-bottom:4px; font-family:'Rajdhani',sans-serif;">Blue: <span id="colorBValue">0</span></label>
        <input type="range" id="colorBSlider" min="0" max="255" value="0" style="width:100%;">
      </div>
    </div>

    <!-- Preset colors -->
    <div style="margin-bottom:24px;">
      <label style="color:rgba(255,255,255,0.7); font-size:12px; display:block; margin-bottom:8px; font-family:'Rajdhani',sans-serif;">Preset Colors</label>
      <div id="colorPresets" style="display:grid; grid-template-columns:repeat(10,1fr); gap:6px;">
        <!-- Row 1: Grayscale -->
        <button class="color-preset" data-color="#FFFFFF" style="height:32px; border:2px solid rgba(0,0,0,0.2); border-radius:4px; cursor:pointer; background:#FFFFFF;"></button>
        <button class="color-preset" data-color="#E0E0E0" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#E0E0E0;"></button>
        <button class="color-preset" data-color="#C0C0C0" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#C0C0C0;"></button>
        <button class="color-preset" data-color="#A0A0A0" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#A0A0A0;"></button>
        <button class="color-preset" data-color="#808080" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#808080;"></button>
        <button class="color-preset" data-color="#606060" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#606060;"></button>
        <button class="color-preset" data-color="#404040" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#404040;"></button>
        <button class="color-preset" data-color="#202020" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#202020;"></button>
        <button class="color-preset" data-color="#101010" style="height:32px; border:2px solid rgba(255,255,255,0.2); border-radius:4px; cursor:pointer; background:#101010;"></button>
        <button class="color-preset" data-color="#000000" style="height:32px; border:2px solid rgba(255,255,255,0.3); border-radius:4px; cursor:pointer; background:#000000;"></button>
        <!-- Row 2: Reds (dark → light) -->
        <button class="color-preset" data-color="#330000" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#330000;"></button>
        <button class="color-preset" data-color="#660000" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#660000;"></button>
        <button class="color-preset" data-color="#990000" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#990000;"></button>
        <button class="color-preset" data-color="#CC0000" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CC0000;"></button>
        <button class="color-preset" data-color="#FF0000" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF0000;"></button>
        <button class="color-preset" data-color="#FF3333" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF3333;"></button>
        <button class="color-preset" data-color="#FF6666" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF6666;"></button>
        <button class="color-preset" data-color="#FF9999" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF9999;"></button>
        <button class="color-preset" data-color="#FFCCCC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFCCCC;"></button>
        <button class="color-preset" data-color="#FFE6E6" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFE6E6;"></button>
        <!-- Row 3: Oranges (dark → light) -->
        <button class="color-preset" data-color="#331A00" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#331A00;"></button>
        <button class="color-preset" data-color="#663300" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#663300;"></button>
        <button class="color-preset" data-color="#994D00" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#994D00;"></button>
        <button class="color-preset" data-color="#CC6600" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CC6600;"></button>
        <button class="color-preset" data-color="#FF6600" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF6600;"></button>
        <button class="color-preset" data-color="#FF8533" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF8533;"></button>
        <button class="color-preset" data-color="#FFA366" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFA366;"></button>
        <button class="color-preset" data-color="#FFC299" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFC299;"></button>
        <button class="color-preset" data-color="#FFE0CC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFE0CC;"></button>
        <button class="color-preset" data-color="#FFF0E6" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFF0E6;"></button>
        <!-- Row 4: Yellows (dark → light) -->
        <button class="color-preset" data-color="#333300" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#333300;"></button>
        <button class="color-preset" data-color="#666600" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#666600;"></button>
        <button class="color-preset" data-color="#999900" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#999900;"></button>
        <button class="color-preset" data-color="#CCCC00" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CCCC00;"></button>
        <button class="color-preset" data-color="#FFFF00" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFFF00;"></button>
        <button class="color-preset" data-color="#FFFF33" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFFF33;"></button>
        <button class="color-preset" data-color="#FFFF66" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFFF66;"></button>
        <button class="color-preset" data-color="#FFFF99" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFFF99;"></button>
        <button class="color-preset" data-color="#FFFFCC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFFFCC;"></button>
        <button class="color-preset" data-color="#FFFFE6" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFFFE6;"></button>
        <!-- Row 5: Greens (dark → light) -->
        <button class="color-preset" data-color="#003300" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#003300;"></button>
        <button class="color-preset" data-color="#006600" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#006600;"></button>
        <button class="color-preset" data-color="#009900" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#009900;"></button>
        <button class="color-preset" data-color="#00CC00" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#00CC00;"></button>
        <button class="color-preset" data-color="#00FF00" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#00FF00;"></button>
        <button class="color-preset" data-color="#33FF33" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#33FF33;"></button>
        <button class="color-preset" data-color="#66FF66" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#66FF66;"></button>
        <button class="color-preset" data-color="#99FF99" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#99FF99;"></button>
        <button class="color-preset" data-color="#CCFFCC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CCFFCC;"></button>
        <button class="color-preset" data-color="#E6FFE6" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#E6FFE6;"></button>
        <!-- Row 6: Cyans (dark → light) -->
        <button class="color-preset" data-color="#003333" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#003333;"></button>
        <button class="color-preset" data-color="#006666" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#006666;"></button>
        <button class="color-preset" data-color="#009999" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#009999;"></button>
        <button class="color-preset" data-color="#00CCCC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#00CCCC;"></button>
        <button class="color-preset" data-color="#00FFFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#00FFFF;"></button>
        <button class="color-preset" data-color="#33FFFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#33FFFF;"></button>
        <button class="color-preset" data-color="#66FFFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#66FFFF;"></button>
        <button class="color-preset" data-color="#99FFFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#99FFFF;"></button>
        <button class="color-preset" data-color="#CCFFFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CCFFFF;"></button>
        <button class="color-preset" data-color="#E6FFFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#E6FFFF;"></button>
        <!-- Row 7: Blues (dark → light) -->
        <button class="color-preset" data-color="#000033" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#000033;"></button>
        <button class="color-preset" data-color="#000066" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#000066;"></button>
        <button class="color-preset" data-color="#000099" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#000099;"></button>
        <button class="color-preset" data-color="#0000CC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#0000CC;"></button>
        <button class="color-preset" data-color="#0000FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#0000FF;"></button>
        <button class="color-preset" data-color="#3333FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#3333FF;"></button>
        <button class="color-preset" data-color="#6666FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#6666FF;"></button>
        <button class="color-preset" data-color="#9999FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#9999FF;"></button>
        <button class="color-preset" data-color="#CCCCFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CCCCFF;"></button>
        <button class="color-preset" data-color="#E6E6FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#E6E6FF;"></button>
        <!-- Row 8: Purples (dark → light) -->
        <button class="color-preset" data-color="#1A0033" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#1A0033;"></button>
        <button class="color-preset" data-color="#330066" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#330066;"></button>
        <button class="color-preset" data-color="#4D0099" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#4D0099;"></button>
        <button class="color-preset" data-color="#6600CC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#6600CC;"></button>
        <button class="color-preset" data-color="#7F13EC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#7F13EC;"></button>
        <button class="color-preset" data-color="#9933FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#9933FF;"></button>
        <button class="color-preset" data-color="#B366FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#B366FF;"></button>
        <button class="color-preset" data-color="#CC99FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CC99FF;"></button>
        <button class="color-preset" data-color="#E6CCFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#E6CCFF;"></button>
        <button class="color-preset" data-color="#F2E6FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#F2E6FF;"></button>
        <!-- Row 9: Magentas/Pinks (dark → light) -->
        <button class="color-preset" data-color="#330033" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#330033;"></button>
        <button class="color-preset" data-color="#660066" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#660066;"></button>
        <button class="color-preset" data-color="#990099" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#990099;"></button>
        <button class="color-preset" data-color="#CC00CC" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#CC00CC;"></button>
        <button class="color-preset" data-color="#FF00FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF00FF;"></button>
        <button class="color-preset" data-color="#FF33FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF33FF;"></button>
        <button class="color-preset" data-color="#FF66FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF66FF;"></button>
        <button class="color-preset" data-color="#FF99FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FF99FF;"></button>
        <button class="color-preset" data-color="#FFCCFF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFCCFF;"></button>
        <button class="color-preset" data-color="#FFE6FF" style="height:32px; border:2px solid transparent; border-radius:4px; cursor:pointer; background:#FFE6FF;"></button>
      </div>
    </div>

    <!-- Actions -->
    <div style="display:flex; gap:12px;">
      <button id="colorPickerCancel" style="
          flex:1; background:rgba(255,255,255,0.1);
          border:1px solid rgba(255,255,255,0.2); color:rgba(255,255,255,0.7);
          padding:12px; border-radius:8px; font-size:14px; font-weight:bold;
          cursor:pointer; text-transform:uppercase; font-family:'Rajdhani',sans-serif;">Cancel</button>
      <button id="colorPickerConfirm" style="
          flex:1; background:var(--primary-accent,#FF6600); border:none;
          color:white; padding:12px; border-radius:8px; font-size:14px;
          font-weight:bold; cursor:pointer; text-transform:uppercase;
          font-family:'Rajdhani',sans-serif;">Confirm</button>
    </div>
  </div>
</div>`;
    document.body.appendChild(_tpl.firstElementChild);

    // ── DOM refs ─────────────────────────────────────────────────
    const modal       = document.getElementById('colorPickerModal');
    const preview     = document.getElementById('colorPreview');
    const hexInput    = document.getElementById('colorHexInput');
    const rSlider     = document.getElementById('colorRSlider');
    const gSlider     = document.getElementById('colorGSlider');
    const bSlider     = document.getElementById('colorBSlider');
    const rValue      = document.getElementById('colorRValue');
    const gValue      = document.getElementById('colorGValue');
    const bValue      = document.getElementById('colorBValue');
    const vSlider     = document.getElementById('colorVSlider');
    const vValue      = document.getElementById('colorVValue');
    const wheelCanvas = document.getElementById('colorWheelCanvas');
    const wheelCursor = document.getElementById('colorWheelCursor');
    const confirmBtn  = document.getElementById('colorPickerConfirm');
    const cancelBtn   = document.getElementById('colorPickerCancel');
    const closeBtn    = document.getElementById('colorPickerClose');

    let currentCallback = null;
    let currentColor    = '#FF6600';
    let isDragging      = false;

    // ── HSV ↔ RGB ────────────────────────────────────────────────
    function hsvToRgb(h, s, v) {
        h = ((h % 360) + 360) % 360;
        const c = v * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c;
        let r, g, b;
        if      (h < 60)  [r,g,b] = [c,x,0];
        else if (h < 120) [r,g,b] = [x,c,0];
        else if (h < 180) [r,g,b] = [0,c,x];
        else if (h < 240) [r,g,b] = [0,x,c];
        else if (h < 300) [r,g,b] = [x,0,c];
        else              [r,g,b] = [c,0,x];
        return [Math.round((r+m)*255), Math.round((g+m)*255), Math.round((b+m)*255)];
    }

    function rgbToHsv(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r,g,b), min = Math.min(r,g,b), diff = max - min;
        let h = 0, s = max === 0 ? 0 : diff / max, v = max;
        if (diff !== 0) {
            if      (max === r) h = ((g - b) / diff % 6) * 60;
            else if (max === g) h = ((b - r) / diff + 2) * 60;
            else                h = ((r - g) / diff + 4) * 60;
            if (h < 0) h += 360;
        }
        return [h, s, v];
    }

    // ── Color wheel ──────────────────────────────────────────────
    function drawColorWheel() {
        const ctx = wheelCanvas.getContext('2d');
        const w = wheelCanvas.width, h = wheelCanvas.height;
        const cx = w / 2, cy = h / 2;
        const radius = Math.min(cx, cy) - 2;
        const brightness = parseInt(vSlider.value) / 100;
        const imgData = ctx.createImageData(w, h);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const dx = x - cx, dy = y - cy;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const idx = (y * w + x) * 4;
                if (dist <= radius) {
                    const hue = ((Math.atan2(dy, dx) * 180 / Math.PI) + 360) % 360;
                    const sat = dist / radius;
                    const [r, g, b] = hsvToRgb(hue, sat, brightness);
                    imgData.data[idx]     = r;
                    imgData.data[idx + 1] = g;
                    imgData.data[idx + 2] = b;
                    imgData.data[idx + 3] = 255;
                }
            }
        }
        ctx.putImageData(imgData, 0, 0);
    }

    function updateCursor(h, s) {
        const cx = wheelCanvas.width  / 2;
        const cy = wheelCanvas.height / 2;
        const radius = Math.min(cx, cy) - 2;
        const angle  = h * Math.PI / 180;
        wheelCursor.style.left = (cx + s * radius * Math.cos(angle)) + 'px';
        wheelCursor.style.top  = (cy + s * radius * Math.sin(angle)) + 'px';
    }

    // ── Sync helpers ─────────────────────────────────────────────
    function updateFromRGB(skipWheelCursor) {
        const r = parseInt(rSlider.value);
        const g = parseInt(gSlider.value);
        const b = parseInt(bSlider.value);
        rValue.textContent = r;
        gValue.textContent = g;
        bValue.textContent = b;
        const hex = '#' + [r,g,b].map(v => v.toString(16).padStart(2,'0')).join('').toUpperCase();
        hexInput.value = hex;
        preview.style.background = hex;
        currentColor = hex;
        if (!skipWheelCursor) {
            const [hh, ss, vv] = rgbToHsv(r, g, b);
            vSlider.value = Math.round(vv * 100);
            vValue.textContent = vSlider.value;
            updateCursor(hh, ss);
        }
    }

    function setColorFromHex(hex) {
        if (!hex || !/^#[0-9A-Fa-f]{6}$/.test(hex)) return;
        const r = parseInt(hex.substr(1,2), 16);
        const g = parseInt(hex.substr(3,2), 16);
        const b = parseInt(hex.substr(5,2), 16);
        rSlider.value = r; gSlider.value = g; bSlider.value = b;
        const [hh, ss, vv] = rgbToHsv(r, g, b);
        vSlider.value = Math.round(vv * 100);
        vValue.textContent = vSlider.value;
        rValue.textContent = r; gValue.textContent = g; bValue.textContent = b;
        hexInput.value = hex.toUpperCase();
        preview.style.background = hex;
        currentColor = hex.toUpperCase();
        updateCursor(hh, ss);
        drawColorWheel();
    }

    // ── Wheel interaction ────────────────────────────────────────
    function pickFromWheel(e) {
        const rect   = wheelCanvas.getBoundingClientRect();
        const scaleX = wheelCanvas.width  / rect.width;
        const scaleY = wheelCanvas.height / rect.height;
        const x  = (e.clientX - rect.left) * scaleX;
        const y  = (e.clientY - rect.top)  * scaleY;
        const cx = wheelCanvas.width  / 2;
        const cy = wheelCanvas.height / 2;
        const dx = x - cx, dy = y - cy;
        const radius = Math.min(cx, cy) - 2;
        const hue = ((Math.atan2(dy, dx) * 180 / Math.PI) + 360) % 360;
        const sat = Math.min(Math.sqrt(dx*dx + dy*dy) / radius, 1);
        const [r, g, b] = hsvToRgb(hue, sat, parseInt(vSlider.value) / 100);
        rSlider.value = r; gSlider.value = g; bSlider.value = b;
        updateCursor(hue, sat);
        updateFromRGB(true);
    }

    wheelCanvas.addEventListener('mousedown', e => { isDragging = true; pickFromWheel(e); e.preventDefault(); });
    document.addEventListener('mousemove',    e => { if (isDragging) pickFromWheel(e); });
    document.addEventListener('mouseup',      ()  => { isDragging = false; });

    // ── Control event handlers (with debouncing/throttling) ──────
    // Throttle RGB sliders: max 1 update every 100ms during drag (smooth visual feedback)
    const throttledUpdateRGB = throttle(() => updateFromRGB(false), 100);
    rSlider.addEventListener('input', throttledUpdateRGB);
    gSlider.addEventListener('input', throttledUpdateRGB);
    bSlider.addEventListener('input', throttledUpdateRGB);

    // Throttle V slider: same logic
    const throttledUpdateV = throttle(function() {
        vValue.textContent = vSlider.value;
        const [hh, ss] = rgbToHsv(parseInt(rSlider.value), parseInt(gSlider.value), parseInt(bSlider.value));
        const [nr, ng, nb] = hsvToRgb(hh, ss, parseInt(vSlider.value) / 100);
        rSlider.value = nr; gSlider.value = ng; bSlider.value = nb;
        updateFromRGB(true);
        drawColorWheel();
    }, 100);
    vSlider.addEventListener('input', throttledUpdateV);

    // Debounce hex input: wait 300ms after user stops typing before validating
    const debouncedSetColor = debounce(color => setColorFromHex(color), 300);
    hexInput.addEventListener('input', e => debouncedSetColor(e.target.value));

    document.querySelectorAll('.color-preset').forEach(btn => {
        btn.addEventListener('click', () => setColorFromHex(btn.dataset.color));
    });

    // ── Open / close ─────────────────────────────────────────────
    function closeModal() {
        modal.style.display = 'none';
        currentCallback = null;
    }

    window.openColorPicker = function(initialColor, callback) {
        currentColor    = initialColor || '#FF6600';
        currentCallback = callback;
        setColorFromHex(currentColor);
        // Move to end of body on every open: ensures correct DOM painter order
        // over any modal that called document.body.appendChild() after us
        // (e.g. quick-effect-creator). z-index alone is not enough when
        // backdrop-filter creates a new compositing layer in the parent.
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    };

    confirmBtn.addEventListener('click', () => { if (currentCallback) currentCallback(currentColor); closeModal(); });
    cancelBtn .addEventListener('click', closeModal);
    closeBtn  .addEventListener('click', closeModal);
    modal     .addEventListener('click', e => { if (e.target === modal) closeModal(); });

})();
