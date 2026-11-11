/**
 * Keyboard Designer — keyboard-designer.html
 *
 * Interactive 2D keyboard matrix visualizer.
 * Connects the static CSS-Grid keyboard layout to real OpenRGB LED data.
 *
 * Features:
 *  - Auto-loads keyboard devices with MATRIX topology
 *  - Maps LED indices from OpenRGB matrix_map to DOM key elements
 *  - Click any key → shows LED index, matrix position, color picker
 *  - Live Preview mode: color picker changes → sent to hardware in real-time
 *  - Color memory: each key remembers its assigned color between selections
 *  - Test Gradient: applies a horizontal gradient to the full keyboard
 *  - Grid Lines toggle: shows/hides per-cell overlay for debugging
 *  - Export JSON: downloads matrix map as JSON file
 *  - Keybind Profile: load Elite Dangerous .binds file → color-code keys by function
 */

// ── State ────────────────────────────────────────────────────
let currentDeviceId  = null;
let currentMatrix    = null;
let livePreviewOn    = false;
let gridLinesOn      = false;
let selectedKeyEl    = null;          // currently selected DOM key element
let selectedLedIndex = null;          // its LED index (integer)

// Per-LED color memory: ledIndex → '#rrggbb'
const keyColors = {};

// Active preset ID: null means no preset loaded, '1'/'2'/'3' = loaded slot
let activePresetId = null;

// Guard flags: prevent listener accumulation when loadMatrix() is called more than once
let _tooltipWired = false;
let _clickWired   = false;

// ── DOM shortcuts ─────────────────────────────────────────────
const $ = id => document.getElementById(id);
const kbd = () => document.getElementById('105-keyboard');

// ── Initialisation ────────────────────────────────────────────

async function init() {
    await loadUserSettings();
    wireButtons();
    await Promise.all([
        loadKeyboardDevices(),
        prefillBindingsPath(),
    ]);
    // Auto-select P1 on startup so the keyboard shows the saved default colors
    await loadPreset('1');
    console.log('[KBD] Ready');
}

/**
 * Pre-populate the bindings path input with the default location
 * so the user immediately sees where we look for the file.
 */
async function prefillBindingsPath() {
    const input = $('bindings-path-input');
    if (!input || input.value.trim()) return;  // already set (e.g. from a previous load)
    try {
        const path = await eel.get_default_bindings_path()();
        if (path) input.value = path;
    } catch (e) {
        console.warn('[KBD] Could not get default bindings path:', e);
    }
}

async function loadUserSettings() {
    const r = await api('get_settings');
    if (r?.language && window.i18n) {
        await window.i18n.init(r.language);
    }
    requestAnimationFrame(() => document.body.classList.add('loaded'));
}

// ── Device loading ────────────────────────────────────────────

async function loadKeyboardDevices() {
    const r = await api('get_keyboard_devices');

    if (!r?.success) {
        showNotification(r?.error || window.i18n.get('notifications.no_keyboard_found') || 'No keyboard devices found', 'warning');
        return;
    }

    if (r.count === 0) {
        showNotification(window.i18n.get('notifications.no_matrix_keyboard') || 'No MATRIX keyboard detected via OpenRGB', 'warning');
        return;
    }

    // Auto-select first device; future enhancement: build a <select> for multiple
    currentDeviceId = r.devices[0].id;
    const name = r.devices[0].name;

    // Update Matrix Info panel title with real device name
    const titleEl = document.querySelector('.sci-fi-border .orbitron[data-i18n="sections.keyboard_designer.layout_title"]');
    if (titleEl) titleEl.textContent = name;

    await loadMatrix(currentDeviceId);
}

async function loadMatrix(deviceId) {
    const r = await api('get_keyboard_matrix', deviceId);

    if (!r?.success) {
        showNotification(r?.error || window.i18n.get('notifications.failed_load_matrix') || 'Failed to load matrix', 'error');
        return;
    }

    currentMatrix = r;

    // Update static Matrix Info panel numbers with real data
    _updateMatrixInfoPanel(r);

    mapMatrixToKeys();
    _wireTooltip();
    showNotification(window.i18n.interpolate('notifications.matrix_loaded', {device: r.device_name, count: r.led_count}) || `Matrix loaded: ${r.device_name} (${r.led_count} LEDs)`, 'success');
}

function _updateMatrixInfoPanel(r) {
    // Update device name in the collapsible Device Info panel
    _updateMatrixDeviceName(r.device_name);
}

// ── Matrix → DOM key mapping ──────────────────────────────────

/**
 * Walk through the OpenRGB matrix_map (row-major, -1 = empty cell)
 * and assign each non-empty LED index to the corresponding DOM key element.
 *
 * The DOM order of .keyboard__key elements inside #105-keyboard matches
 * the row-major read order of the matrix_map: both go left-to-right,
 * top-to-bottom, skipping hidden/spacer slots.
 */
function mapMatrixToKeys() {
    if (!currentMatrix) return;

    const container = kbd();
    if (!container) return;

    // Collect visible (non-hidden) key elements in DOM order
    const domKeys = Array.from(
        container.querySelectorAll('.keyboard__key:not(.keyboard__key--hidden)')
    );

    // Flatten matrix to ordered LED-index list (skip -1 empty cells)
    const ledOrder = currentMatrix.matrix_map
        .flat()
        .filter(cell => cell !== -1);

    console.log(`[KBD] Mapping ${ledOrder.length} LEDs to ${domKeys.length} DOM keys`);

    // If LED names are available from the API, use name-based matching
    // to avoid positional offset bugs (e.g. indicator LEDs in the matrix
    // that have no corresponding DOM key).
    const ledNames = currentMatrix.led_names || {};   // {idx_str: "Key: Z"}
    const hasNames = Object.keys(ledNames).length > 0;

    if (hasNames) {
        // Build reverse map: normalized_key_text → led_index
        // OpenRGB names are "Key: Z", "Key: Space", "Key: Left Shift", etc.
        const nameToIndex = {};
        for (const [idxStr, name] of Object.entries(ledNames)) {
            const normalized = _normalizeKeyName(name);
            if (normalized) nameToIndex[normalized] = parseInt(idxStr);
        }

        domKeys.forEach(keyEl => {
            const keyText = (keyEl.dataset.keyText || keyEl.textContent.trim()).toLowerCase();
            const normalized = _normalizeKeyText(keyText);
            const ledIdx = nameToIndex[normalized];
            if (ledIdx !== undefined) {
                keyEl.dataset.ledIndex = ledIdx;
            }
        });

        // Fallback: positional mapping for any key that didn't match by name
        domKeys.forEach((keyEl, i) => {
            if (!keyEl.dataset.ledIndex && i < ledOrder.length) {
                keyEl.dataset.ledIndex = ledOrder[i];
            }
        });

    } else {
        // No LED names available — use positional mapping
        domKeys.forEach((keyEl, i) => {
            if (i >= ledOrder.length) return;
            keyEl.dataset.ledIndex = ledOrder[i];
        });
    }

    // Wire click → selectKey via delegation on the container (once only).
    if (!_clickWired) {
        _clickWired = true;
        container.addEventListener('click', e => {
            const keyEl = e.target.closest('.keyboard__key:not(.keyboard__key--hidden)');
            if (keyEl) selectKey(keyEl);
        });
    }
}

/**
 * Normalize an OpenRGB LED name to a lookup key.
 * "Key: Left Shift" → "left shift"
 * "Key: Z"          → "z"
 * "Key: Num 7"      → "num 7"
 * "Key: Num Add"    → "num +"   (ASUS/Corsair sometimes use "Add"/"Sub" labels)
 * "Key: Num Period" → "num del" (same canonical target as _normalizeKeyText "num_.")
 */
function _normalizeKeyName(name) {
    if (!name) return null;
    const lower = name.toLowerCase();
    if (!lower.startsWith('key: ')) return null;
    let key = lower.slice(5).trim();
    // Normalize numpad operator label variants so they match _normalizeKeyText output
    if (key === 'num add')                          key = 'num +';
    if (key === 'num sub' || key === 'num subtract') key = 'num -';
    if (key === 'num period' || key === 'num .')    key = 'num del';
    // ISO keyboards: backslash near Left Shift is called "Non-US Backslash" in OpenRGB.
    // Normalize to 'backslash' so the DOM '\' key maps to the correct physical LED
    // instead of falling back to the positional mapping (which lands on Delete).
    if (key === 'non-us backslash' || key === 'backslash iso' || key === 'iso backslash') key = 'backslash';
    return key;
}

/**
 * Normalize a DOM key text for matching against OpenRGB names.
 * Maps HTML text representations to OpenRGB name conventions.
 */
function _normalizeKeyText(text) {
    if (!text) return '';
    const t = text.toLowerCase().trim();
    const MAP = {
        'esc': 'escape',
        '`': 'grave',
        '-': 'minus',
        '=': 'equals',
        '[': 'left bracket',
        ']': 'right bracket',
        '\\': 'backslash',
        ';': 'semicolon',
        "'": 'quote',
        ',': 'comma',
        '.': 'period',
        '/': 'slash',
        'ins': 'insert',
        'del': 'delete',
        'prtsc': 'print screen', 'print screen': 'print screen',
        'pause': 'pause',
        'caps': 'caps lock', 'capslock': 'caps lock',
        'num lock': 'num lock',
        'scroll lock': 'scroll lock',
        '÷': 'num slash', 'num /': 'num slash',
        '×': 'num asterisk', 'num *': 'num asterisk',
        '↑': 'up arrow', '←': 'left arrow', '↓': 'down arrow', '→': 'right arrow',
        'backspace': 'backspace', 'tab': 'tab', 'enter': 'enter',
        'shift': 'left shift',   // default shift = left
        'ctrl': 'left ctrl',
        'alt': 'left alt',
        'win': 'left windows',
        'menu': 'menu',
        'space': 'space',
        'home': 'home', 'end': 'end',
        'page up': 'page up', 'page down': 'page down',
        'num lock': 'num lock',
    };
    if (MAP[t]) return MAP[t];

    // Numpad digit/special keys use "num_X" in DOM but OpenRGB names them "Num X"
    // e.g. data-key-text="num_7"  →  OpenRGB "Key: Num 7"  →  normalized "num 7"
    //      data-key-text="num_."  →  OpenRGB "Key: Num Del" →  normalized "num del"
    if (t.startsWith('num_')) {
        const suffix = t.slice(4);
        // The numpad decimal key is labeled "Del" in OpenRGB for most keyboards
        if (suffix === '.') return 'num del';
        return 'num ' + suffix;   // "num_7" → "num 7",  "num_enter" → "num enter"
    }

    return t;
}

// ── Key selection ─────────────────────────────────────────────

function selectKey(keyEl) {
    const ledIdx = parseInt(keyEl.dataset.ledIndex);
    if (isNaN(ledIdx)) return;

    // Deselect previous
    if (selectedKeyEl) selectedKeyEl.classList.remove('keyboard__key--selected');

    // Select new
    keyEl.classList.add('keyboard__key--selected');
    selectedKeyEl    = keyEl;
    selectedLedIndex = ledIdx;

    // Populate panel
    const keyLabel = (keyEl.dataset.keyText || '?').toUpperCase();
    const matrixPos = _findMatrixPos(ledIdx);
    const hasColor = ledIdx in keyColors;
    const currentColor = keyColors[ledIdx] || null;

    $('selected-key-placeholder').style.display = 'none';
    $('selected-key-info').classList.remove('hidden');

    $('info-key-label').textContent  = keyLabel;
    $('info-led-index').textContent  = ledIdx;
    $('info-matrix-pos').textContent = matrixPos;

    // Sync color swatch: colored if assigned, gray if default
    const colorBtn = $('key-color-btn');
    if (colorBtn) {
        colorBtn.style.background = hasColor ? currentColor : 'rgba(255,255,255,0.15)';
    }
    $('info-color-hex').textContent = hasColor ? currentColor.toUpperCase() : '— default';
}

function _findMatrixPos(ledIdx) {
    if (!currentMatrix) return '—';
    const map = currentMatrix.matrix_map;
    for (let r = 0; r < map.length; r++) {
        for (let c = 0; c < map[r].length; c++) {
            if (map[r][c] === ledIdx) return `(${r}, ${c})`;
        }
    }
    return '—';
}

// ── Color contrast helper ─────────────────────────────────────

/**
 * Returns '#000000' if the hex color is light (high luminance),
 * '#ffffff' if dark. Used to keep key labels readable.
 */
function _contrastColor(hex) {
    const h = hex.replace('#', '');
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    // Perceived brightness (ITU-R BT.601)
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness > 140 ? '#000000' : '#ffffff';
}

/**
 * Single rendering function for ALL key colorization paths
 * (preset load, color picker, profile apply).
 *
 * Uses an LED-style look: semi-transparent fill (60%) + colored border +
 * soft glow — consistent whether the color comes from a preset or a
 * keybinding category.  Pass null to reset to the default dark key.
 */
function _applyColorToKey(keyEl, hex) {
    if (!keyEl) return;
    if (hex) {
        keyEl.style.background  = hex + '99';                          // ~60% opacity fill
        keyEl.style.borderColor = hex;
        keyEl.style.boxShadow   = `0 0 6px ${hex}99, 0 0 14px ${hex}33`; // LED glow
        keyEl.style.color       = _contrastColor(hex);
    } else {
        keyEl.style.background  = '';
        keyEl.style.borderColor = '';
        keyEl.style.boxShadow   = '';
        keyEl.style.color       = '';
    }
}

// ── Color picker interaction ──────────────────────────────────

function onColorPickerChange(hexColor) {
    if (selectedLedIndex === null) return;

    // Update color memory
    keyColors[selectedLedIndex] = hexColor;

    // Update color swatch button + hex label
    const colorBtn = $('key-color-btn');
    if (colorBtn) colorBtn.style.background = hexColor;
    $('info-color-hex').textContent = hexColor.toUpperCase();

    // Update DOM key — adapts label contrast for light colors
    _applyColorToKey(selectedKeyEl, hexColor);
    _updateLedCountLabel();

    // Send to hardware only if live preview is active
    if (livePreviewOn && currentDeviceId !== null) {
        api('set_key_color', currentDeviceId, selectedLedIndex, hexColor)
            .then(r => {
                if (!r?.success) console.warn('[KBD] set_key_color failed:', r?.error);
            });
    }
}

// ── Clear key color ────────────────────────────────────────────

function clearKeyColor() {
    if (selectedLedIndex === null) return;

    // Remove from color memory
    delete keyColors[selectedLedIndex];

    // Reset DOM key to default appearance (also restores default text color)
    _applyColorToKey(selectedKeyEl, null);
    _updateLedCountLabel();

    // Reset swatch to gray + label to "—"
    const colorBtn = $('key-color-btn');
    if (colorBtn) colorBtn.style.background = 'rgba(255,255,255,0.15)';
    const hexLabel = $('info-color-hex');
    if (hexLabel) hexLabel.textContent = '— default';

    // If live preview: send black to hardware (LED off)
    if (livePreviewOn && currentDeviceId !== null) {
        api('set_key_color', currentDeviceId, selectedLedIndex, '000000')
            .then(r => {
                if (!r?.success) console.warn('[KBD] clear key color failed:', r?.error);
            });
    }
}

// ── Page exit restore ─────────────────────────────────────────

/**
 * Called when the user navigates away from Keyboard Designer.
 * Fires test_gradient_preview (white→white) to leave the keyboard
 * fully lit rather than in a partial / dark state from live preview.
 * Fire-and-forget: the 300ms navigation fade gives enough time to complete.
 */
async function _restoreKeyboardOnExit() {
    if (currentDeviceId === null) return;
    try {
        await api('test_gradient_preview', currentDeviceId, '#FFFFFF', '#FFFFFF', 'horizontal');
    } catch (_) {}
}

// ── Live Preview toggle ───────────────────────────────────────

/**
 * Send the complete virtual keyboard state to hardware in one batch.
 * Every LED in the matrix_map is included: keyColors[idx] or '#000000'.
 * Called when Live Preview is enabled and after bulk color operations.
 */
async function _flushToHardware() {
    if (!currentDeviceId || !currentMatrix) return;

    const ledColors = {};
    currentMatrix.matrix_map.flat().forEach(idx => {
        if (idx !== -1) ledColors[String(idx)] = keyColors[idx] || '#000000';
    });
    if (Object.keys(ledColors).length === 0) return;

    const r = await api('apply_keyboard_profile', ledColors);
    if (!r?.success) console.warn('[KBD] _flushToHardware failed:', r?.error);
}

function toggleLivePreview() {
    livePreviewOn = !livePreviewOn;

    // Update all three live-preview buttons
    [$('btn-live-preview'), $('btn-toggle-preview')].forEach(btn => {
        if (!btn) return;
        btn.classList.toggle('active', livePreviewOn);
    });

    // Top-bar label + icon
    const lblEl  = $('label-live-preview');
    const iconEl = $('icon-live-preview');
    if (lblEl)  lblEl.textContent  = livePreviewOn ? 'LIVE  ON' : 'LIVE PREVIEW';
    if (iconEl) iconEl.textContent = livePreviewOn ? 'visibility_off' : 'visibility';

    // Sidebar label + icon
    const lblSb  = $('label-live-preview-sb');
    const iconSb = $('icon-live-preview-sb');
    if (lblSb)  lblSb.textContent  = livePreviewOn ? 'Live Preview: ON' : 'Toggle Live Preview';
    if (iconSb) iconSb.textContent = livePreviewOn ? 'visibility_off' : 'visibility';

    // Status dots (top bar + sidebar)
    const dotStyle = livePreviewOn
        ? 'background:#22c55e; box-shadow:0 0 6px rgba(34,197,94,.8);'
        : 'background:rgba(255,255,255,0.2);';
    [$('live-preview-dot'), $('live-preview-dot-sb')].forEach(dot => {
        if (dot) dot.style.cssText = dotStyle;
    });

    showNotification(livePreviewOn ? (window.i18n.get('notifications.live_preview_on') || 'Live Preview enabled') : (window.i18n.get('notifications.live_preview_off') || 'Live Preview disabled'), livePreviewOn ? 'success' : 'info');

    // On activation: immediately sync physical keyboard with virtual state.
    // Uncolored LEDs go black so hardware mirrors the virtual keyboard exactly.
    if (livePreviewOn) _flushToHardware();
}

// ── Clear all key colors ───────────────────────────────────────

function clearAllColors() {
    if (!Object.keys(keyColors).length) {
        showNotification(window.i18n.get('notifications.no_colors_to_clear') || 'No colors to clear', 'info');
        return;
    }
    const count = Object.keys(keyColors).length;
    Object.keys(keyColors).forEach(k => delete keyColors[+k]);
    document.querySelectorAll('.keyboard__key').forEach(k => _applyColorToKey(k, null));
    _updateLedCountLabel();
    showNotification(window.i18n.interpolate('notifications.cleared_colors', {count}) || `Cleared ${count} color assignment${count !== 1 ? 's' : ''}`, 'info');
    // Mirror the all-black state to hardware if live preview is active
    if (livePreviewOn) _flushToHardware();
}

// ── LED count label (bottom of keyboard) ──────────────────────

function _updateLedCountLabel() {
    const el = $('led-count-label');
    if (!el) return;
    const n = Object.keys(keyColors).length;
    el.textContent = n > 0 ? `${n} LED${n !== 1 ? 's' : ''} configured` : '';
}

// ── Matrix Info collapsible ────────────────────────────────────

function toggleMatrixInfo() {
    const body    = $('matrix-info-body');
    const chevron = $('matrix-info-chevron');
    if (!body) return;
    const open = body.classList.toggle('hidden');
    if (chevron) chevron.textContent = open ? 'expand_more' : 'expand_less';
}

// Update device name in the collapsible panel
function _updateMatrixDeviceName(name) {
    const el = $('matrix-device-name');
    if (el) el.textContent = name || '—';
}

// ── Grid lines toggle ─────────────────────────────────────────

function toggleGridLines() {
    gridLinesOn = !gridLinesOn;
    kbd()?.classList.toggle('keyboard--grid', gridLinesOn);

    const lblEl  = $('label-grid');
    const iconEl = $('icon-grid');
    if (lblEl)  lblEl.textContent  = gridLinesOn ? 'Hide Grid Lines' : 'Show Grid Lines';
    if (iconEl) iconEl.textContent = gridLinesOn ? 'grid_off' : 'grid_on';
}

// ── Test Gradient ─────────────────────────────────────────────

async function testGradient() {
    if (currentDeviceId === null) {
        showNotification(window.i18n.get('notifications.no_keyboard_selected') || 'No keyboard selected', 'warning');
        return;
    }
    // Cycle through a few preset gradients for demo purposes
    const presets = [
        { start: '#FF6600', end: '#0066FF', dir: 'horizontal', label: 'Orange → Blue' },
        { start: '#FF0000', end: '#00FF00', dir: 'horizontal', label: 'Red → Green' },
        { start: '#6600FF', end: '#FF6600', dir: 'vertical',   label: 'Purple → Orange (vertical)' },
        { start: '#00FFFF', end: '#FF00FF', dir: 'diagonal',   label: 'Cyan → Magenta (diagonal)' },
    ];
    testGradient._idx = ((testGradient._idx ?? -1) + 1) % presets.length;
    const p = presets[testGradient._idx];

    showNotification(window.i18n.interpolate('notifications.gradient_applying', {label: p.label}) || `Applying gradient: ${p.label}...`, 'info');
    const r = await api('test_gradient_preview', currentDeviceId, p.start, p.end, p.dir);
    if (r?.success) {
        showNotification(window.i18n.interpolate('notifications.gradient_applied', {label: p.label}) || `Gradient applied (3s): ${p.label}`, 'success');
    } else {
        showNotification(r?.error || window.i18n.get('notifications.gradient_failed') || 'Gradient failed', 'error');
    }
}

// ── Keyboard Presets ──────────────────────────────────────────

function _updatePresetButtons(selectedId) {
    // Highlight the selected preset-slot container + its select button
    document.querySelectorAll('.preset-slot').forEach(slot => {
        const isActive = slot.dataset.preset === String(selectedId);
        slot.style.borderColor = isActive ? 'var(--primary-accent)' : '';
        const selectBtn = slot.querySelector('.preset-select-btn');
        if (selectBtn) {
            selectBtn.style.color = isActive ? 'var(--primary-accent)' : '';
        }
    });
}

function _updatePresetStatus(id, msg) {
    const el = $('preset-status');
    if (!el) return;
    el.textContent = msg || (id ? `Saving to: P${id}` : 'Select a slot above');
    el.style.color = id ? 'rgba(255,102,0,0.7)' : 'rgba(255,255,255,0.3)';
}

/** Select a preset slot as the save target — does NOT load from disk. */
function selectPresetSlot(id) {
    activePresetId = String(id);
    _updatePresetButtons(id);
    _updatePresetStatus(id, `Saving to: P${id} — press SAVE PRESET to write`);
}

async function loadPreset(id) {
    const r = await api('load_keyboard_preset', String(id));
    if (!r?.success) {
        showNotification(r?.error || window.i18n.get('notifications.failed_load_preset') || 'Failed to load preset', 'error');
        return;
    }
    // Clear current key colors and apply preset data to DOM
    Object.keys(keyColors).forEach(k => delete keyColors[k]);
    const lc = r.led_colors || {};
    // Reset all DOM keys to default (clears background, border, boxShadow, color)
    document.querySelectorAll('.keyboard__key').forEach(k => {
        _applyColorToKey(k, null);
    });
    Object.entries(lc).forEach(([idx, rgb]) => {
        const hex = rgbToHex(rgb[0], rgb[1], rgb[2]);
        keyColors[+idx] = hex;
        // Find DOM key with this LED index and apply color with contrast
        const keyEl = document.querySelector(`.keyboard__key[data-led-index="${idx}"]`);
        _applyColorToKey(keyEl, hex);
    });
    activePresetId = String(id);
    _updatePresetButtons(id);
    const n = Object.keys(lc).length;
    _updatePresetStatus(id, `P${id} loaded from disk (${n} LEDs) · Saving to: P${id}`);
    _updateLedCountLabel();
    showNotification(window.i18n.interpolate('notifications.preset_loaded', {id, count: n}) || `Preset ${id} loaded (${n} LEDs)`, 'success');
}

async function savePreset() {
    if (!activePresetId) {
        showNotification(window.i18n.get('notifications.no_preset_selected') || 'Select a preset slot first (P1 / P2 / P3)', 'warning');
        return;
    }
    // Convert keyColors {idx: "#RRGGBB"} → {idx_str: [r, g, b]}
    const ledColors = {};
    Object.entries(keyColors).forEach(([idx, hex]) => {
        const rgb = hexToRgb(hex);
        if (rgb) ledColors[String(idx)] = [rgb[0], rgb[1], rgb[2]];
    });
    const r = await api('save_keyboard_preset', activePresetId, ledColors);
    if (r?.success) {
        showNotification(window.i18n.interpolate('notifications.preset_saved', {id: activePresetId, count: r.saved_leds}) || `Preset ${activePresetId} saved (${r.saved_leds} LEDs)`, 'success');
        _updatePresetStatus(activePresetId, `Preset ${activePresetId} saved`);
    } else {
        showNotification(r?.error || window.i18n.get('notifications.save_failed') || 'Save failed', 'error');
    }
}

// ── Export JSON ───────────────────────────────────────────────

async function exportJSON() {
    if (currentDeviceId === null) {
        showNotification(window.i18n.get('notifications.no_keyboard_selected') || 'No keyboard selected', 'warning');
        return;
    }

    const r = await api('export_matrix_json', currentDeviceId);
    if (!r?.success) {
        showNotification(r?.error || window.i18n.get('notifications.export_failed') || 'Export failed', 'error');
        return;
    }

    const blob = new Blob([r.json_data], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), { href: url, download: r.filename });
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showNotification(window.i18n.interpolate('notifications.exported_file', {filename: r.filename}) || `Exported: ${r.filename}`, 'success');
}

// ── Category Colors Panel ─────────────────────────────────────

// User-defined overrides for category colors. Null = use profile defaults.
let _customCategoryColors = {};   // { category: [r, g, b] }

// Macro-group structure for the panel layout
const CAT_GROUPS = [
    {
        label: 'Ship Controls',
        cats: ['flight', 'speed', 'combat', 'target', 'navigation', 'ship'],
        catLabels: { flight: 'Flight', speed: 'Speed', combat: 'Combat',
                     target: 'Target', navigation: 'Navig.', ship: 'Ship Sys.' }
    },
    { label: 'General',  cats: ['interface'], catLabels: { interface: 'Interface' } },
    {
        label: 'SRV',
        cats: ['srv_drive', 'srv_combat', 'srv_turret', 'srv_util'],
        catLabels: { srv_drive: 'Drive', srv_combat: 'Combat', srv_turret: 'Turret', srv_util: 'Utility' }
    },
    {
        label: 'On Foot',
        cats: ['onfoot_move', 'onfoot_combat', 'onfoot_item', 'onfoot_interact'],
        catLabels: { onfoot_move: 'Move', onfoot_combat: 'Combat', onfoot_item: 'Items', onfoot_interact: 'Interact' }
    },
];

function _getEffectiveColor(cat) {
    if (_customCategoryColors[cat]) return _customCategoryColors[cat];
    if (_profileColors && _profileColors[cat]) return _profileColors[cat];
    // Default from CATEGORY_COLORS_MAP (hex → [r,g,b])
    const hex = CATEGORY_COLORS_MAP[cat] || '#646464';
    const h = hex.replace('#', '');
    return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
}

function _buildCategoryColorsPanel() {
    const body = $('cat-colors-body');
    if (!body) return;
    body.innerHTML = '';

    CAT_GROUPS.forEach(group => {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'flex flex-col min-w-0';
        groupDiv.innerHTML = `<div class="cat-group-label">${group.label}</div>
            <div class="cat-swatch-row"></div>`;
        const row = groupDiv.querySelector('.cat-swatch-row');

        group.cats.forEach(cat => {
            const rgb = _getEffectiveColor(cat);
            const hex = '#' + rgb.map(v => v.toString(16).padStart(2,'0')).join('');
            const glow = hex + '88';

            const item = document.createElement('div');
            item.className = 'cat-swatch-item';
            item.dataset.cat = cat;
            item.innerHTML = `
                <button class="cat-swatch-btn" title="${group.catLabels[cat]} — click to change"
                    style="background:${hex + '99'};
                           border-color:${hex};
                           box-shadow:0 0 6px ${glow}"></button>
                <span class="cat-swatch-label">${group.catLabels[cat]}</span>`;

            item.querySelector('.cat-swatch-btn').addEventListener('click', () => {
                openColorPicker(hex, newHex => {
                    const h = newHex.replace('#', '');
                    _customCategoryColors[cat] = [
                        parseInt(h.slice(0,2),16),
                        parseInt(h.slice(2,4),16),
                        parseInt(h.slice(4,6),16)
                    ];
                    // Rebuild panel to reflect new color
                    _buildCategoryColorsPanel();
                });
            });

            row.appendChild(item);
        });

        body.appendChild(groupDiv);
    });
}

function _showCategoryColorsPanel() {
    const panel = $('cat-colors-panel');
    if (!panel) return;
    panel.classList.remove('hidden');
    _buildCategoryColorsPanel();
}

// ── Keybind Color Profile ─────────────────────────────────────

// Current profile state
let _profileModes      = null;   // { ship|srv|onfoot|universal|other → { key → {category,func} } }
let _profileColors     = null;   // { category → [r,g,b] }
let _currentMode       = 'ship'; // active mode tab

// Derived from _profileModes + _currentMode (universal always merged in)
let _profileCategories = null;   // { display_key → category }  — current view

// Category human labels for the legend
const CATEGORY_LABELS = {
    flight:     'Flight / Manoeuvring',
    speed:      'Speed / Throttle',
    combat:     'Combat',
    target:     'Targeting',
    navigation: 'Navigation / FSD',
    ship:       'Ship Systems',
    interface:  'Interface / Panels',
    srv:        'SRV',
    onfoot:     'On Foot (Odyssey)',
    other:      'Other (uncategorised)',
};

/**
 * Load the ED keybindings file and display the profile.
 */
async function loadBindings() {
    const btn = $('btn-load-bindings');
    if (btn) { btn.disabled = true; btn.querySelector('span:last-child').textContent = 'Loading...'; }

    try {
        // Use manually entered/browsed path if present, otherwise auto-detect
        const customPath = $('bindings-path-input')?.value?.trim() || null;
        const r = await api('get_keybind_categories', customPath);

        if (!r?.success) {
            showNotification(r?.error || window.i18n.get('notifications.failed_load_keybindings') || 'Could not load keybindings', 'error');
            $('profile-status').textContent = r?.error || 'Load failed';
            return;
        }

        _profileModes  = r.modes  || {};
        _profileColors = r.colors;
        _currentMode   = 'ship';

        // Compute initial view: ship + universal
        _profileCategories = _mergeMode('ship');
        const initBindings = _mergeBindings('ship');

        // Show resolved path in input (useful when auto-detected)
        if (r.file_path && $('bindings-path-input')) {
            $('bindings-path-input').value = r.file_path;
        }

        // Update status bar
        const fileName = r.file_path ? r.file_path.split(/[\\/]/).pop() : '?';
        const total = Object.keys(_profileCategories).length;
        const uncat = r.uncategorised || 0;
        const extra = uncat > 0 ? `  ·  ${uncat} uncategorised` : '';
        $('profile-status').textContent = `${fileName}  ·  ${total} keys${extra}`;

        // Reset mode tabs to Ship active
        document.querySelectorAll('.mode-btn').forEach(btn => {
            const isActive = btn.dataset.mode === 'ship';
            btn.style.background  = isActive ? 'rgba(255,102,0,0.15)' : 'transparent';
            btn.style.borderColor = isActive ? 'rgba(255,102,0,0.4)'  : 'rgba(255,255,255,0.12)';
            btn.style.color       = isActive ? '#FF6600'              : 'rgba(255,255,255,0.4)';
        });

        // Build legend + keybind list
        _buildProfileLegend(r.colors, r.stats);
        _buildKeybindList(_profileCategories, initBindings, r.colors);

        // Colour the DOM keys
        _applyProfileToDOM(_profileCategories, r.colors);
        _updateLedCountLabel();

        // Show mode selector, legend, actions
        $('profile-mode-selector')?.classList.remove('hidden');
        $('profile-legend')?.classList.remove('hidden');
        $('profile-actions')?.classList.remove('hidden');
        $('profile-stats')?.classList.remove('hidden');

        // Show the category colors panel (with reset for any previous customizations)
        _customCategoryColors = {};
        _showCategoryColorsPanel();

        showNotification(window.i18n.interpolate('notifications.profile_loaded', {count: Object.keys(r.categories).length}) || `Keybind profile loaded: ${Object.keys(r.categories).length} keys`, 'success');

    } finally {
        if (btn) { btn.disabled = false; btn.querySelector('span:last-child').textContent = 'Load ED Keybindings'; }
    }
}

/**
 * Build the merged categories for the current mode:
 * universal (always) + selected mode, mode wins on conflict.
 */
/**
 * Merge universal + mode-specific entries (mode wins on conflict).
 * Returns { key → full entry {category, func} }.
 * Call sites extract .category or .func as needed.
 */
function _mergeEntries(mode) {
    if (!_profileModes) return {};
    const merged = { ...(_profileModes.universal || {}) };
    for (const [key, entry] of Object.entries(_profileModes[mode] || {})) {
        merged[key] = entry;
    }
    return merged;
}

function _mergeMode(mode) {
    const entries = _mergeEntries(mode);
    return Object.fromEntries(Object.entries(entries).map(([k, v]) => [k, v.category]));
}

function _mergeBindings(mode) {
    const entries = _mergeEntries(mode);
    return Object.fromEntries(Object.entries(entries).map(([k, v]) => [k, v.func]));
}

/**
 * Switch the active mode tab and refresh DOM + list.
 */
function _switchMode(mode) {
    _currentMode = mode;

    // Update tab button styles
    document.querySelectorAll('.mode-btn').forEach(btn => {
        const isActive = btn.dataset.mode === mode;
        btn.style.background    = isActive ? 'rgba(255,102,0,0.15)' : 'transparent';
        btn.style.borderColor   = isActive ? 'rgba(255,102,0,0.4)'  : 'rgba(255,255,255,0.12)';
        btn.style.color         = isActive ? '#FF6600'              : 'rgba(255,255,255,0.4)';
    });

    // Recompute merged view
    _profileCategories = _mergeMode(mode);
    const bindings     = _mergeBindings(mode);

    // Refresh DOM colors and list
    if (_profileColors) {
        _applyProfileToDOM(_profileCategories, _profileColors);
        _buildKeybindList(_profileCategories, bindings, _profileColors);
    }
}

/**
 * Convert an ED function name (camelCase) to a readable label.
 * "YawLeftButton" → "Yaw Left"
 * "HumanoidSprintButton" → "Sprint"
 * "UseBoostJuice" → "Use Boost Juice"
 */
function _formatFuncName(name) {
    return name
        .replace(/^Humanoid/, '')          // strip On Foot prefix
        .replace(/^Buggy(?=[A-Z])/, '')    // strip SRV prefix
        .replace(/Button$/, '')            // strip trailing "Button"
        .replace(/Toggle$/, ' Toggle')     // keep Toggle as word
        .replace(/([A-Z])/g, ' $1')        // split camelCase
        .replace(/\s+/g, ' ')
        .trim();
}

/** All rows data — kept for live filtering */
let _allRows = [];   // [{ key, funcName, category, hex }]

/**
 * Build the scrollable keybind list rows.
 */
function _buildKeybindList(categories, bindings, colors) {
    // Build sorted row data: by category order, then by key
    const CAT_ORDER = ['flight','speed','combat','target','navigation','ship','interface','srv','onfoot'];

    _allRows = Object.entries(categories).map(([key, cat]) => {
        const rgb = colors[cat] || [128, 128, 128];
        const hex = '#' + rgb.map(v => v.toString(16).padStart(2, '0')).join('');
        return {
            key:      key,
            funcName: bindings[key] || '',
            category: cat,
            hex:      hex,
        };
    }).sort((a, b) => {
        const catDiff = CAT_ORDER.indexOf(a.category) - CAT_ORDER.indexOf(b.category);
        return catDiff !== 0 ? catDiff : a.key.localeCompare(b.key);
    });

    _renderKeybindRows('');

    // Show the list container
    $('profile-keybind-list-wrap')?.classList.remove('hidden');

    // Wire up live search
    const searchEl = $('profile-search');
    if (searchEl) {
        searchEl.value = '';
        searchEl.oninput = () => _renderKeybindRows(searchEl.value.toLowerCase().trim());
    }
}

/**
 * Render (or re-render with filter) the keybind rows.
 */
function _renderKeybindRows(query) {
    const list = $('profile-keybind-list');
    if (!list) return;

    const filtered = query
        ? _allRows.filter(r =>
            r.key.toLowerCase().includes(query) ||
            _formatFuncName(r.funcName).toLowerCase().includes(query) ||
            r.category.includes(query))
        : _allRows;

    list.innerHTML = filtered.map(r => {
        const label = _formatFuncName(r.funcName);
        const keyDisplay = r.key === ' ' ? 'Space' : r.key.toUpperCase();
        return `
        <div class="flex items-center gap-2 px-1 py-1 rounded hover:bg-white/5 transition-colors">
            <div style="width:8px; height:8px; border-radius:2px; flex-shrink:0;
                        background:${r.hex}; box-shadow:0 0 4px ${r.hex}88;"></div>
            <span style="font-family:'Rajdhani',monospace; font-weight:700; font-size:11px;
                         color:${r.hex}; flex-shrink:0; min-width:28px;">${keyDisplay}</span>
            <span style="font-size:11px; color:rgba(255,255,255,0.55);
                         white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
                  title="${label}">${label}</span>
        </div>`;
    }).join('');

    if (filtered.length === 0) {
        list.innerHTML = `<div class="text-xs text-white/50 px-1 py-2">${window.i18n.get('common.no_results') || 'No matches'}</div>`;
    }
}

/**
 * Build the category legend in the sidebar.
 */
function _buildProfileLegend(colors, stats) {
    const legend = $('profile-legend');
    if (!legend) return;
    legend.innerHTML = '';

    // Only show categories that have at least 1 key mapped
    const activeCategories = Object.keys(stats || {}).sort();

    activeCategories.forEach(cat => {
        const rgb   = colors[cat] || [128,128,128];
        const hex   = '#' + rgb.map(v => v.toString(16).padStart(2,'0')).join('').toUpperCase();
        const label = CATEGORY_LABELS[cat] || cat;
        const count = stats[cat] || 0;

        const row = document.createElement('div');
        row.className = 'flex items-center gap-2';
        row.innerHTML = `
            <div style="width:12px; height:12px; border-radius:2px; background:${hex};
                        flex-shrink:0; box-shadow:0 0 4px ${hex}66;"></div>
            <span class="text-xs text-white/70 flex-1">${label}</span>
            <span class="text-xs text-white/50">${count}</span>`;
        legend.appendChild(row);
    });

    // Stats summary
    const statsEl = $('profile-stats');
    if (statsEl) {
        const total = Object.values(stats || {}).reduce((a, b) => a + b, 0);
        statsEl.textContent = `${total} bindings across ${activeCategories.length} categories`;
    }
}

/**
 * Colour each DOM key according to its category.
 * Resets keys that are not in the profile to their default style.
 */
function _applyProfileToDOM(categories, colors) {
    const container = kbd();
    if (!container) return;

    const domKeys = container.querySelectorAll('.keyboard__key:not(.keyboard__key--hidden)');

    // ── Pass 1: apply colors to bound keys, track claimed LED indices ─
    // Multiple DOM keys can share the same ledIdx (positional-mapping
    // artefact: e.g. ↑ and num_1 both get LED 82).  We must set the
    // color BEFORE any delete runs, then only delete indices that were
    // never claimed.
    const claimedLedIdx = new Set();

    domKeys.forEach(keyEl => {
        const keyText = (keyEl.dataset.keyText || '').toLowerCase().trim();
        const cat     = categories[keyText];
        const ledIdx  = parseInt(keyEl.dataset.ledIndex);

        if (cat && (colors[cat] || _customCategoryColors[cat])) {
            if (cat === 'other') {
                // Uncategorised: subtle indicator only, not saved to preset
                keyEl.style.background  = 'rgba(100,100,100,0.15)';
                keyEl.style.borderColor = 'rgba(100,100,100,0.35)';
                keyEl.style.boxShadow   = '';
                keyEl.style.color       = '';
            } else {
                const rgb = _getEffectiveColor(cat);
                const hex = '#' + rgb.map(v => v.toString(16).padStart(2, '0')).join('');
                _applyColorToKey(keyEl, hex);
                if (!isNaN(ledIdx)) {
                    keyColors[ledIdx] = hex;
                    claimedLedIdx.add(ledIdx);
                }
            }
        }
    });

    // ── Pass 2: clear unbound keys, skipping ledIdx already claimed ───
    domKeys.forEach(keyEl => {
        const keyText = (keyEl.dataset.keyText || '').toLowerCase().trim();
        const cat     = categories[keyText];
        const ledIdx  = parseInt(keyEl.dataset.ledIndex);

        if (!(cat && (colors[cat] || _customCategoryColors[cat]))) {
            if (!claimedLedIdx.has(ledIdx)) {
                _applyColorToKey(keyEl, null);
                if (!isNaN(ledIdx)) delete keyColors[ledIdx];
            }
            // If the ledIdx was claimed by another key in pass 1,
            // just reset the visual without touching keyColors.
            else if (cat !== 'other') {
                _applyColorToKey(keyEl, null);
            }
        }
    });

    _updateLedCountLabel();
}

/**
 * Send the profile color map to OpenRGB hardware.
 * Builds { led_index: "#RRGGBB" } using data-led-index attributes already in DOM.
 */
async function applyProfileToHardware() {
    if (!_profileCategories || !_profileColors) {
        showNotification(window.i18n.get('notifications.load_profile_first') || 'Load a keybinding profile first', 'warning');
        return;
    }

    const container = kbd();
    if (!container) return;

    const ledColors = {};
    const domKeys = container.querySelectorAll('.keyboard__key:not(.keyboard__key--hidden)');

    domKeys.forEach(keyEl => {
        const ledIdx  = keyEl.dataset.ledIndex;
        if (ledIdx === undefined) return;

        const keyText = (keyEl.dataset.keyText || '').toLowerCase().trim();
        const cat     = _profileCategories[keyText];
        if (!cat || !_profileColors[cat]) return;

        const rgb = _profileColors[cat];
        const hex = '#' + rgb.map(v => v.toString(16).padStart(2,'0')).join('').toUpperCase();
        ledColors[ledIdx] = hex;
    });

    if (Object.keys(ledColors).length === 0) {
        showNotification(window.i18n.get('notifications.no_led_mapping') || 'No LED mapping available — load matrix data first', 'warning');
        return;
    }

    const r = await api('apply_keyboard_profile', ledColors);
    if (r?.success) {
        showNotification(window.i18n.interpolate('notifications.profile_applied', {count: r.applied}) || `Profile applied: ${r.applied} LEDs colored`, 'success');
    } else {
        showNotification(r?.error || window.i18n.get('notifications.failed_apply_profile') || 'Failed to apply profile', 'error');
    }
}

/**
 * Clear the profile: reset DOM colors and turn off hardware LEDs.
 */
async function clearProfile() {
    _profileCategories = null;
    _profileColors     = null;

    // Reset DOM
    const container = kbd();
    if (container) {
        container.querySelectorAll('.keyboard__key:not(.keyboard__key--hidden)').forEach(keyEl => {
            keyEl.style.background  = '';
            keyEl.style.borderColor = '';
            keyEl.style.boxShadow   = '';
        });
    }

    // Also clear keyColors memory
    Object.keys(keyColors).forEach(k => delete keyColors[k]);

    // Clear hardware
    await api('clear_keyboard_profile');

    // Reset profile state
    _profileModes      = null;
    _profileColors     = null;
    _profileCategories = null;
    _currentMode       = 'ship';
    _allRows = [];

    // Update UI
    $('profile-status').textContent = 'No profile loaded';
    $('profile-mode-selector')?.classList.add('hidden');
    $('profile-legend')?.classList.add('hidden');
    $('profile-keybind-list-wrap')?.classList.add('hidden');
    $('profile-actions')?.classList.add('hidden');
    $('profile-stats')?.classList.add('hidden');

    showNotification(window.i18n.get('notifications.profile_cleared') || 'Profile cleared', 'info');
}


// ── Button wiring ─────────────────────────────────────────────

function wireButtons() {
    // Top bar
    $('btn-live-preview')?.addEventListener('click', toggleLivePreview);
    $('btn-export-map')?.addEventListener('click', exportJSON);

    // Preset select buttons (left part of split button) — select slot, no load
    document.querySelectorAll('.preset-select-btn').forEach(btn => {
        btn.addEventListener('click', () => selectPresetSlot(btn.dataset.preset));
    });
    // Preset load buttons (↓ icon, right part) — load from disk
    document.querySelectorAll('.preset-load-btn').forEach(btn => {
        btn.addEventListener('click', () => loadPreset(btn.dataset.preset));
    });
    $('btn-save-preset')?.addEventListener('click', savePreset);

    // Sidebar Quick Actions
    $('btn-toggle-preview')?.addEventListener('click', toggleLivePreview);
    $('btn-test-gradient')?.addEventListener('click', testGradient);
    $('btn-show-grid')?.addEventListener('click', toggleGridLines);
    $('btn-clear-all')?.addEventListener('click', clearAllColors);
    $('btn-export-json')?.addEventListener('click', exportJSON);

    // Matrix Info collapsible
    $('btn-toggle-matrix-info')?.addEventListener('click', toggleMatrixInfo);

    // Category colors panel
    $('btn-reset-cat-colors')?.addEventListener('click', () => {
        _customCategoryColors = {};
        _buildCategoryColorsPanel();
        if (_profileCategories && _profileColors) {
            _applyProfileToDOM(_profileCategories, _profileColors);
        }
        showNotification(window.i18n.get('notifications.category_colors_reset') || 'Category colors reset to defaults', 'info');
    });
    $('btn-reapply-cat-colors')?.addEventListener('click', () => {
        if (_profileCategories && _profileColors) {
            _applyProfileToDOM(_profileCategories, _profileColors);
            showNotification(window.i18n.get('notifications.keyboard_updated_colors') || 'Keyboard updated with new category colors', 'success');
        } else {
            showNotification(window.i18n.get('notifications.load_profile_first') || 'Load a keybinding profile first', 'warning');
        }
    });

    // Color swatch button → opens shared color picker modal
    $('key-color-btn')?.addEventListener('click', () => {
        const current = keyColors[selectedLedIndex] || '#FF6600';
        openColorPicker(current, onColorPickerChange);
    });
    $('key-color-clear-btn')?.addEventListener('click', clearKeyColor);

    // Browse button → opens native OS file dialog
    $('btn-browse-bindings')?.addEventListener('click', async () => {
        const path = await eel.browse_bindings_file()();
        if (path) {
            $('bindings-path-input').value = path;
        }
    });

    // Keybind profile
    $('btn-load-bindings')?.addEventListener('click', loadBindings);
    $('btn-apply-profile')?.addEventListener('click', applyProfileToHardware);
    $('btn-clear-profile')?.addEventListener('click', clearProfile);

    // Mode selector tabs
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => _switchMode(btn.dataset.mode));
    });

    console.log('[KBD] Buttons wired');
}

// ── Key tooltip ────────────────────────────────────────────────

const CATEGORY_COLORS_MAP = {
    // Ship
    flight:          '#0077FF', speed:           '#00CCFF', combat:    '#FF1E1E',
    target:          '#FF7800', navigation:      '#00DC64', ship:      '#FFD200',
    // General
    interface:       '#A050FF',
    // SRV
    srv_drive:       '#0077FF', srv_combat:      '#FF1E1E',
    srv_turret:      '#FF7800', srv_util:        '#FFD200',
    // On Foot
    onfoot_move:     '#0077FF', onfoot_combat:   '#FF1E1E',
    onfoot_item:     '#FF7800', onfoot_interact: '#A050FF',
    // Legacy fallback
    srv:    '#00DCB4', onfoot: '#96FF3C', other: '#646464',
};

const MODE_LABELS = { ship: 'Ship', srv: 'SRV', onfoot: 'On Foot', universal: 'UI' };

function _showTooltip(keyEl, mouseX, mouseY) {
    const tip   = document.getElementById('key-tooltip');
    if (!tip) return;

    const keyText = (keyEl.dataset.keyText || '').toLowerCase().trim();
    const ledIdx  = parseInt(keyEl.dataset.ledIndex);
    const keyName = (keyEl.dataset.keyText || '?').toUpperCase();

    // ── Collect bindings from all modes ──────────────────────────
    const modeBlocks = [];
    if (_profileModes) {
        for (const [mode, data] of Object.entries(_profileModes)) {
            if (data[keyText]) {
                const { category, func } = data[keyText];
                modeBlocks.push({ mode, label: MODE_LABELS[mode] || mode, category, func });
            }
        }
    }

    // ── Color assigned via preset ────────────────────────────────
    const colorHex = (!isNaN(ledIdx) && keyColors[ledIdx]) ? keyColors[ledIdx] : null;

    // ── Build HTML ───────────────────────────────────────────────
    let html = `
        <div class="kt-header">
            <span class="kt-key-name">${keyName}</span>
            ${!isNaN(ledIdx) ? `<span class="kt-led-idx">LED ${ledIdx}</span>` : ''}
        </div>`;

    if (modeBlocks.length === 0 && !colorHex) {
        html += `<div class="kt-no-data">No bindings assigned</div>`;
    } else {
        // Group by mode
        const byMode = {};
        for (const b of modeBlocks) {
            if (!byMode[b.label]) byMode[b.label] = [];
            byMode[b.label].push(b);
        }
        for (const [label, bindings] of Object.entries(byMode)) {
            html += `<div class="kt-mode-block">
                <div class="kt-mode-label">${label}</div>`;
            for (const b of bindings) {
                const dotColor = CATEGORY_COLORS_MAP[b.category] || '#646464';
                html += `<div class="kt-action">
                    <span class="kt-cat-dot" style="background:${dotColor}"></span>
                    <span class="kt-func">${_formatFuncName(b.func)}</span>
                    <span class="kt-cat-label">${b.category}</span>
                </div>`;
            }
            html += `</div>`;
        }
    }

    if (colorHex) {
        html += `<div class="kt-color-row">
            <span class="kt-color-swatch" style="background:${colorHex}"></span>
            <span class="kt-color-hex">${colorHex.toUpperCase()}</span>
        </div>`;
    }

    tip.innerHTML = html;
    tip.style.display = 'block';
    _positionTooltip(tip, mouseX, mouseY);
}

function _positionTooltip(tip, x, y) {
    const W = tip.offsetWidth  || 200;
    const H = tip.offsetHeight || 100;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const GAP = 14;

    let left = x + GAP;
    let top  = y - GAP - H;   // above cursor by default

    if (left + W > vw - 8)  left = x - W - GAP;   // flip left
    if (top < 8)             top  = y + GAP;        // flip below
    if (top + H > vh - 8)   top  = vh - H - 8;

    tip.style.left = left + 'px';
    tip.style.top  = top  + 'px';
}

function _hideTooltip() {
    const tip = document.getElementById('key-tooltip');
    if (tip) tip.style.display = 'none';
}

function _wireTooltip() {
    if (_tooltipWired) return;
    _tooltipWired = true;
    const container = kbd();
    if (!container) return;

    // Delegated: one listener on the keyboard container handles all keys
    container.addEventListener('mouseenter', e => {
        const keyEl = e.target.closest('.keyboard__key:not(.keyboard__key--hidden)');
        if (keyEl) _showTooltip(keyEl, e.clientX, e.clientY);
    }, true);

    container.addEventListener('mousemove', e => {
        const tip = document.getElementById('key-tooltip');
        if (tip && tip.style.display !== 'none') {
            _positionTooltip(tip, e.clientX, e.clientY);
        }
    });

    container.addEventListener('mouseleave', e => {
        // Only hide when actually leaving the container (not just moving between keys)
        if (!container.contains(e.relatedTarget)) _hideTooltip();
    }, true);
}

// ── Boot ──────────────────────────────────────────────────────

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
