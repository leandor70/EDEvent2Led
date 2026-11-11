/**
 * devices.js - Device Testing Screen
 *
 * Real Eel API integration for RGB device testing.
 *
 * Sections:
 * - Flash Test: quick device identification via white flash
 * - Effect Preview: run saved VisualEffects from library on hardware
 * - Hardware Modes: native firmware animations
 *
 * Device enable/disable is client-side only (Set<id>).
 */

// ========================================
// STATE
// ========================================

let devices = [];
let selectedDeviceId = null;
let selectedEffectId = null;   // ID of selected VisualEffect from library
let hardwareModes = [];        // { index, name, has_speed, has_colors }
const enabledDeviceIds = new Set();
let deviceConfigs = {};        // config_key → { enabled, on_disable } — persisted via device_config_api

// ========================================
// INITIALIZATION
// ========================================

async function initTestScreen() {
    console.log('[devices.js] Initializing...');
    // setupHardwareModeDropdown(); // REMOVED - Hardware Modes feature removed due to OpenRGB SDK limitations
    setupSliders();
    setupButtons();
    await loadDevices();
    await loadVisualEffects();
    console.log('[devices.js] Ready');
}

// ========================================
// HARDWARE MODE DROPDOWN - REMOVED
// ========================================
// Feature removed: OpenRGB SDK doesn't support reliable parameter control
// Most hardware modes require speed/colors to function, which can't be set via API

/**
 * Initialize the single custom dropdown for hardware modes.
 * Uses event delegation on the menu element so dynamically injected
 * items work without re-wiring listeners after setDropdownOptions().
 */
function setupHardwareModeDropdown() {
    const dropdown = document.getElementById('hardware-mode-selector-dropdown');
    if (!dropdown) return;

    const button = dropdown.querySelector('.dropdown-button');
    const menu = dropdown.querySelector('.dropdown-menu');
    const selectedSpan = button.querySelector('.dropdown-selected');

    button.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = !menu.classList.contains('hidden');
        if (isOpen) {
            menu.classList.add('hidden');
            button.classList.remove('active');
        } else {
            menu.classList.remove('hidden');
            button.classList.add('active');
        }
    });

    // Event delegation: works even after menu.innerHTML replacement
    menu.addEventListener('click', (e) => {
        const item = e.target.closest('.dropdown-item');
        if (!item) return;

        menu.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
        selectedSpan.textContent = item.textContent.trim();
        menu.classList.add('hidden');
        button.classList.remove('active');
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('#hardware-mode-selector-dropdown')) {
            menu.classList.add('hidden');
            button.classList.remove('active');
        }
    });
}

/**
 * Get selected value from the hardware mode dropdown.
 * @returns {string|null}
 */
function getHardwareModeValue() {
    const item = document.querySelector('#hardware-mode-selector-dropdown .dropdown-item.selected');
    return item ? item.dataset.value : null;
}

/**
 * Replace hardware mode dropdown items dynamically.
 * @param {Array<{value: string|number, label: string}>} options
 */
function setHardwareModeOptions(options) {
    const dropdown = document.getElementById('hardware-mode-selector-dropdown');
    if (!dropdown) return;

    const menu = dropdown.querySelector('.dropdown-menu');
    const selectedSpan = dropdown.querySelector('.dropdown-selected');

    const selectModeLabel = (window.i18n && window.i18n.get('pages.device_testing.select_mode')) || '-- Select Mode --';
    const placeholder = `<li class="dropdown-item px-4 py-3 text-sm text-white cursor-pointer transition-colors selected" data-value="-1">${escapeHtml(selectModeLabel)}</li>`;
    const items = options.map(opt =>
        `<li class="dropdown-item px-4 py-3 text-sm text-white cursor-pointer transition-colors" data-value="${opt.value}">${escapeHtml(String(opt.label))}</li>`
    ).join('');

    menu.innerHTML = placeholder + items;
    selectedSpan.textContent = selectModeLabel;
}

// ========================================
// SLIDERS
// ========================================

function setupSliders() {
    const hwSpeedSlider = document.getElementById('hw-speed-slider');
    const hwSpeedValue = document.getElementById('hw-speed-value');
    if (hwSpeedSlider && hwSpeedValue) {
        hwSpeedSlider.addEventListener('input', () => {
            hwSpeedValue.textContent = hwSpeedSlider.value;
        });
    }
}

// ========================================
// BUTTONS
// ========================================

function setupButtons() {
    document.getElementById('flash-btn')?.addEventListener('click', () => {
        if (selectedDeviceId === null) { showNotification(window.i18n.get('notifications.no_device_selected') || 'No device selected', 'warning'); return; }
        flashDevice(selectedDeviceId);
    });

    document.getElementById('flash-all-btn')?.addEventListener('click', flashAllDevices);
    document.getElementById('export-devices-btn')?.addEventListener('click', exportDeviceInfo);

    document.getElementById('preview-effect-btn')?.addEventListener('click', previewEffectUI);
    document.getElementById('stop-effect-btn')?.addEventListener('click', stopEffectUI);
    document.getElementById('clear-btn')?.addEventListener('click', clearEffect);

    // Hardware Modes buttons - REMOVED (feature removed due to SDK limitations)
    // document.getElementById('activate-hw-mode-btn')?.addEventListener('click', activateHardwareModeUI);
    // document.getElementById('activate-hw-mode-all-btn')?.addEventListener('click', activateHardwareModeAllUI);
    // document.getElementById('restore-direct-btn')?.addEventListener('click', () => restoreDirectMode(selectedDeviceId));
}

// ========================================
// DEVICE MANAGEMENT
// ========================================

async function loadDevices() {
    // Load devices and persisted config in parallel
    const [result, cfgResult] = await Promise.all([
        api('get_devices'),
        eel.get_device_config()()
    ]);

    if (!result || !result.success) {
        renderOfflineState();
        showNotification(result?.error || window.i18n.get('notifications.failed_load_devices') || 'Failed to load devices', 'error');
        return;
    }

    devices = result.devices;

    // Populate deviceConfigs from persisted storage
    if (cfgResult?.success) deviceConfigs = cfgResult.config || {};

    // Init enabledDeviceIds from persisted config (default: enabled)
    enabledDeviceIds.clear();
    devices.forEach(d => {
        const cfg = deviceConfigs[d.config_key];
        if (!cfg || cfg.enabled !== false) {
            enabledDeviceIds.add(d.id);
        }
    });

    renderDeviceList();

    if (devices.length > 0) {
        await selectDevice(devices[0].id);
    }
}

function getDeviceIcon(type) {
    const icons = {
        'keyboard': 'keyboard',
        'mouse': 'mouse',
        'strip': 'lightbulb',
        'motherboard': 'computer',
        'gpu': 'videogame_asset',
        'cooler': 'ac_unit',
    };
    return icons[type?.toLowerCase()] || 'device_hub';
}

function renderDeviceList() {
    const container = document.getElementById('device-list-container');
    if (!container) return;

    if (devices.length === 0) {
        renderOfflineState();
        return;
    }

    container.innerHTML = '';
    devices.forEach(device => container.appendChild(createDeviceCard(device)));
}

function createDeviceCard(device) {
    const isSelected = device.id === selectedDeviceId;
    const isEnabled = enabledDeviceIds.has(device.id);
    const topologyClass = device.topology === 'MATRIX' ? 'matrix' : device.topology === 'LINEAR' ? 'linear' : 'single';
    const iconName = getDeviceIcon(device.type);

    // Get persisted on_disable preference for this device
    const cfg = deviceConfigs[device.config_key] || {};
    const onDisable = cfg.on_disable || 'keep';
    const disableColorRgb = cfg.disable_color || [0, 0, 0];
    const disableColorHex = '#' + disableColorRgb.map(v => v.toString(16).padStart(2, '0')).join('');

    const dimLabel = device.dimensions?.length >= 2
        ? `<span class="text-gray-400 text-xs">Matrix: <span class="text-white">${device.dimensions[0]}x${device.dimensions[1]}</span></span>`
        : device.dimensions?.length === 1
        ? `<span class="text-gray-400 text-xs">Line: <span class="text-white">${device.dimensions[0]}</span></span>`
        : '';

    const card = document.createElement('div');
    card.className = `device-card${isSelected ? ' selected' : ''}${!isEnabled ? ' disabled' : ''}`;
    card.dataset.deviceId = device.id;

    card.innerHTML = `
        <div style="display:flex;align-items:center;gap:12px;">
            <div class="device-icon">
                <span class="material-symbols-outlined" style="font-size:32px;color:var(--primary-accent);">${iconName}</span>
            </div>
            <div style="flex:1;min-width:0;">
                <h3 style="font-size:15px;font-weight:600;margin-bottom:4px;color:${isEnabled ? '#fff' : '#888'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(device.name)}</h3>
                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                    <span class="topology-badge ${topologyClass}">${device.topology}</span>
                    <span class="led-count-badge">${device.led_count} LEDs</span>
                    ${dimLabel}
                </div>
            </div>
            <label class="glass-toggle-container" title="${isEnabled ? 'Click to disable' : 'Click to enable'}">
                <input type="checkbox" class="glass-toggle-input"${isEnabled ? ' checked' : ''}/>
                <div class="glass-toggle-track"><div class="glass-toggle-thumb"></div></div>
            </label>
        </div>
        <div class="on-disable-row">
            <span class="on-disable-label">Idle:</span>
            <select class="on-disable-select">
                <option value="keep"${onDisable === 'keep' ? ' selected' : ''}>Keep colors</option>
                <option value="hardware"${onDisable === 'hardware' ? ' selected' : ''}>Hardware mode</option>
                <option value="off"${onDisable === 'off' ? ' selected' : ''}>Turn off</option>
                <option value="color"${onDisable === 'color' ? ' selected' : ''}>Fade to color</option>
                <option value="ambilight"${onDisable === 'ambilight' ? ' selected' : ''}>Ambilight</option>
            </select>
            <button class="disable-color-swatch" title="Click to choose fade color"
                    data-color="${disableColorHex}"
                    style="background:${disableColorHex};display:${onDisable === 'color' ? 'inline-block' : 'none'};"></button>
            ${onDisable === 'ambilight' ? '<span class="ambilight-idle-badge">&#9788;</span>' : ''}
        </div>
        ${device.topology === 'LINEAR' ? `
        <div class="on-disable-row" style="margin-top:6px;">
            <span class="on-disable-label" style="color:rgba(255,255,255,0.5);">Topology Editor:</span>
            <label class="glass-toggle-container" style="transform:scale(0.82);transform-origin:left center;" title="Include this device in the Topology Editor">
                <input type="checkbox" class="glass-toggle-input topology-editor-toggle"${cfg.topology_editor ? ' checked' : ''}/>
                <div class="glass-toggle-track"><div class="glass-toggle-thumb"></div></div>
            </label>
        </div>` : ''}
    `;

    // Card click → select device (ignore toggle and on-disable dropdown)
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.glass-toggle-container') && !e.target.closest('.on-disable-row') && !e.target.closest('.disable-color-picker')) {
            selectDevice(device.id);
        }
    });

    // Toggle: persist enabled/disabled state via API
    card.querySelector('.glass-toggle-input').addEventListener('change', async (e) => {
        e.stopPropagation();
        const enabled = e.target.checked;
        if (enabled) {
            enabledDeviceIds.add(device.id);
        } else {
            enabledDeviceIds.delete(device.id);
        }
        // Update local cache immediately (before API call)
        if (!deviceConfigs[device.config_key]) deviceConfigs[device.config_key] = {};
        deviceConfigs[device.config_key].enabled = enabled;
        // Persist to backend (fire-and-forget; UI already updated)
        eel.set_device_enabled(device.config_key, enabled)();
        renderDeviceList();
    });

    // On-disable dropdown: persist preference via API, sync ambilight, toggle color swatch
    card.querySelector('.on-disable-select').addEventListener('change', async (e) => {
        e.stopPropagation();
        const value = e.target.value;
        const prevValue = (deviceConfigs[device.config_key] || {}).on_disable || 'keep';

        if (!deviceConfigs[device.config_key]) deviceConfigs[device.config_key] = { enabled: true };
        deviceConfigs[device.config_key].on_disable = value;
        eel.set_device_on_disable(device.config_key, value)();

        // Sync with ambilight service
        if (value === 'ambilight') {
            eel.set_ambilight_device_enabled(device.config_key, true)();
        } else if (prevValue === 'ambilight') {
            eel.set_ambilight_device_enabled(device.config_key, false)();
        }

        const swatch = card.querySelector('.disable-color-swatch');
        if (swatch) swatch.style.display = value === 'color' ? 'inline-block' : 'none';

        // Re-render card to show/hide ambilight badge
        renderDeviceList();
    });

    // Topology Editor toggle (LINEAR devices only)
    card.querySelector('.topology-editor-toggle')?.addEventListener('change', (e) => {
        e.stopPropagation();
        const enabled = e.target.checked;
        if (!deviceConfigs[device.config_key]) deviceConfigs[device.config_key] = { enabled: true };
        deviceConfigs[device.config_key].topology_editor = enabled;
        eel.set_device_topology_editor(device.config_key, enabled)();
    });

    // Color swatch button: open custom color picker modal
    card.querySelector('.disable-color-swatch').addEventListener('click', (e) => {
        e.stopPropagation();
        const swatch = e.currentTarget;
        const currentHex = swatch.dataset.color || '#000000';
        openColorPicker(currentHex, (hex) => {
            // Update swatch appearance
            swatch.style.background = hex;
            swatch.dataset.color = hex;
            // Persist to backend
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            if (!deviceConfigs[device.config_key]) deviceConfigs[device.config_key] = { enabled: true };
            deviceConfigs[device.config_key].disable_color = [r, g, b];
            eel.set_device_disable_color(device.config_key, [r, g, b])();
        });
    });

    return card;
}

function renderOfflineState() {
    const container = document.getElementById('device-list-container');
    if (!container) return;
    container.innerHTML = `
        <div class="text-center py-12">
            <span class="material-symbols-outlined" style="font-size:48px;color:#ef4444;display:block;margin-bottom:16px;">wifi_off</span>
            <h3 style="font-size:16px;color:white;margin-bottom:8px;">${(window.i18n && window.i18n.get('common.openrgb_not_connected')) || 'OpenRGB Not Connected'}</h3>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:16px;">${(window.i18n && window.i18n.get('common.openrgb_not_connected_hint')) || 'Make sure OpenRGB is running on localhost:6742'}</p>
            <button onclick="loadDevices()"
                class="bg-orange-500/10 border border-orange-500 text-orange-400 px-4 py-2 rounded text-sm hover:bg-orange-500/20">
                Retry
            </button>
        </div>
    `;
}

async function selectDevice(deviceId) {
    selectedDeviceId = deviceId;
    renderDeviceList();
    await loadHardwareModes(deviceId);
}

function getEnabledDevices() {
    return devices.filter(d => enabledDeviceIds.has(d.id));
}

// ========================================
// FLASH TESTING
// ========================================

async function flashDevice(deviceId) {
    const result = await api('flash_device', deviceId);
    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.flash_failed') || 'Flash failed', 'error');
    }
}

async function flashAllDevices() {
    const result = await api('flash_all_devices');
    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.flash_all_failed') || 'Flash all failed', 'error');
        return;
    }
    showNotification(result.message || window.i18n.get('notifications.flashing_all') || 'Flashing all devices...', 'success');
}

// ========================================
// EFFECT PREVIEW (VisualEffect library)
// ========================================

/**
 * Load all VisualEffects from the library and populate the preview list.
 */
async function loadVisualEffects() {
    const container = document.getElementById('effect-preview-list');
    if (!container) return;

    const result = await api('get_effects_list');

    if (!result || !result.success) {
        container.innerHTML = `
            <div style="text-align:center; padding:24px; color:rgba(255,255,255,0.4); font-size:13px;">
                <span class="material-symbols-outlined" style="font-size:32px; display:block; margin-bottom:8px; color:rgba(255,100,0,0.4);">error_outline</span>
                Could not load effects library
            </div>`;
        return;
    }

    const effects = result.effects || [];

    if (effects.length === 0) {
        container.innerHTML = `
            <div style="text-align:center; padding:24px; color:rgba(255,255,255,0.4); font-size:13px;">
                <span class="material-symbols-outlined" style="font-size:32px; display:block; margin-bottom:8px; opacity:0.4;">auto_awesome</span>
                ${window.i18n.get('common.no_effects_yet') || 'No effects in library yet.'}<br>
                <span style="font-size:11px; margin-top:4px; display:block;">${window.i18n.get('common.create_effects_hint') || 'Create effects in the Effects Editor first.'}</span>
            </div>`;
        return;
    }

    renderEffectList(effects);
}

/**
 * Render compact effect cards in the preview list.
 * @param {Array} effects
 */
function renderEffectList(effects) {
    const container = document.getElementById('effect-preview-list');
    if (!container) return;

    container.innerHTML = '';

    effects.forEach(effect => {
        const isSelected = effect.id === selectedEffectId;
        const stepCount = effect.steps?.length || 0;

        const card = document.createElement('div');
        card.className = `effect-preview-card${isSelected ? ' selected' : ''}`;
        card.dataset.effectId = effect.id;

        card.innerHTML = `
            <span class="material-symbols-outlined" style="font-size:20px; color:${isSelected ? 'var(--primary-accent)' : 'rgba(255,255,255,0.35)'}; flex-shrink:0;">auto_awesome</span>
            <div style="flex:1; min-width:0;">
                <div style="font-size:14px; font-weight:600; color:${isSelected ? '#fff' : 'rgba(255,255,255,0.85)'}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(effect.name)}</div>
                <div style="font-size:11px; color:rgba(255,255,255,0.4); margin-top:1px;">${stepCount} step${stepCount !== 1 ? 's' : ''}${effect.description ? ' · ' + escapeHtml(effect.description.substring(0, 40)) : ''}</div>
            </div>
            <span style="font-size:10px; padding:3px 8px; border-radius:4px; background:rgba(255,102,0,0.1); color:rgba(255,102,0,0.8); text-transform:uppercase; letter-spacing:0.05em; flex-shrink:0;">${escapeHtml(effect.category || 'custom')}</span>
        `;

        card.addEventListener('click', () => selectEffect(effect.id));
        container.appendChild(card);
    });
}

/**
 * Mark an effect as selected. Re-renders the list to update highlight.
 * @param {string} effectId
 */
function selectEffect(effectId) {
    selectedEffectId = effectId;
    // Re-render cards to update selection highlight
    document.querySelectorAll('#effect-preview-list .effect-preview-card').forEach(card => {
        const isSelected = card.dataset.effectId === effectId;
        card.classList.toggle('selected', isSelected);
        const icon = card.querySelector('.material-symbols-outlined');
        const nameEl = card.querySelector('div > div:first-child');
        if (icon) icon.style.color = isSelected ? 'var(--primary-accent)' : 'rgba(255,255,255,0.35)';
        if (nameEl) nameEl.style.color = isSelected ? '#fff' : 'rgba(255,255,255,0.85)';
    });
}

/**
 * Run the selected VisualEffect on all connected devices.
 */
async function previewEffectUI() {
    if (!selectedEffectId) {
        showNotification(window.i18n.get('notifications.select_effect_first') || 'Select an effect from the list first', 'warning');
        return;
    }

    const result = await api('test_effect_on_devices', selectedEffectId);

    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.preview_failed') || 'Preview failed', 'error');
        return;
    }
    showNotification(result.message || window.i18n.get('notifications.playing_effect') || 'Playing effect...', 'success');
}

/**
 * Stop any currently running effect.
 */
async function stopEffectUI() {
    const result = await api('stop_current_effect');
    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.failed_stop_effect') || 'Failed to stop effect', 'error');
    }
}

/**
 * Turn off LEDs on the currently selected device (set all to black).
 */
async function clearEffect() {
    if (selectedDeviceId === null) {
        showNotification(window.i18n.get('notifications.no_device_selected') || 'No device selected', 'warning');
        return;
    }
    const result = await api('set_static_color', selectedDeviceId, '#000000', 1.0);
    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.failed_clear') || 'Failed to clear', 'error');
    }
}

// ========================================
// HARDWARE MODES
// ========================================

async function loadHardwareModes(deviceId) {
    const result = await api('get_hardware_modes', deviceId);

    if (!result || !result.success) {
        console.warn('[devices.js] Failed to load hardware modes:', result?.error);
        hardwareModes = [];
        setHardwareModeOptions([]);
        return;
    }

    hardwareModes = result.modes;
    setHardwareModeOptions(hardwareModes.map(m => ({ value: m.index, label: m.name })));

    console.log(`[devices.js] Loaded ${hardwareModes.length} hardware modes for device ${deviceId}`);
}

async function activateHardwareModeUI() {
    if (selectedDeviceId === null) {
        showNotification(window.i18n.get('notifications.no_device_selected') || 'No device selected', 'warning');
        return;
    }

    const modeIndexStr = getHardwareModeValue();
    if (modeIndexStr === null || modeIndexStr === '-1') {
        showNotification(window.i18n.get('notifications.no_mode_selected') || 'Select a hardware mode', 'warning');
        return;
    }

    const modeIndex = parseInt(modeIndexStr);

    const result = await api('activate_hardware_mode', selectedDeviceId, modeIndex, null, null);
    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.failed_activate_mode') || 'Failed to activate mode', 'error');
        return;
    }
    showNotification(result.message || window.i18n.get('notifications.hw_mode_activated') || 'Hardware mode activated', 'success');
}

async function activateHardwareModeAllUI() {
    const modeIndexStr = getHardwareModeValue();
    if (modeIndexStr === null || modeIndexStr === '-1') {
        showNotification(window.i18n.get('notifications.no_mode_selected') || 'Select a hardware mode', 'warning');
        return;
    }

    const modeIndex = parseInt(modeIndexStr);

    let errorCount = 0;
    for (const device of getEnabledDevices()) {
        const result = await api('activate_hardware_mode', device.id, modeIndex, null, null);
        if (!result || !result.success) {
            showNotification(`${device.name}: ${result?.error || 'Error'}`, 'error');
            errorCount++;
        }
    }

    if (errorCount === 0) {
        showNotification(window.i18n.interpolate('notifications.hardware_mode_activated_all', {count: getEnabledDevices().length}) || `Hardware mode activated on ${getEnabledDevices().length} device(s)`, 'success');
    }
}

async function restoreDirectMode(deviceId) {
    if (deviceId === null) {
        showNotification(window.i18n.get('notifications.no_device_selected') || 'No device selected', 'warning');
        return;
    }
    const result = await api('restore_direct_mode', deviceId);
    if (!result || !result.success) {
        showNotification(result?.error || window.i18n.get('notifications.failed_restore_direct') || 'Failed to restore Direct mode', 'error');
        return;
    }
    showNotification(window.i18n.get('notifications.restored_direct') || 'Restored to Direct mode', 'success');
}

// ========================================
// EXPORT
// ========================================

function exportDeviceInfo() {
    if (devices.length === 0) {
        showNotification(window.i18n.get('notifications.no_devices_export') || 'No devices to export', 'warning');
        return;
    }

    const data = {
        timestamp: new Date().toISOString(),
        device_count: devices.length,
        devices
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `devices_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showNotification(window.i18n.get('notifications.device_info_exported') || 'Device info exported', 'success');
}

// ========================================
// HELPERS
// ========================================
// NOTE: escapeHtml() is defined in common.js (imported globally)
// ========================================
// i18n + FADE-IN
// ========================================

async function loadUserSettings() {
    const result = await api('get_settings');
    if (result?.language && window.i18n) {
        await window.i18n.init(result.language);
    }
    requestAnimationFrame(() => {
        document.body.classList.add('loaded');
    });
}

// ========================================
// ENTRY POINT
// ========================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
        await loadUserSettings();
        await initTestScreen();
    });
} else {
    (async () => {
        await loadUserSettings();
        await initTestScreen();
    })();
}
