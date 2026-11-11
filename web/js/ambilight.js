'use strict';

// ── State ─────────────────────────────────────────────────────────────────────

let _cfg   = {};
let _devs  = [];

// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('load', async () => {
    const [cfg, devs] = await Promise.all([
        api('get_ambilight_config'),
        api('get_ambilight_devices'),
    ]);
    _cfg  = cfg  || {};
    _devs = devs || [];

    applyConfig(_cfg);
    renderDevices(_devs, _cfg);
    setInterval(pollStatus, 800);
});

// ── Config apply ──────────────────────────────────────────────────────────────

function applyConfig(cfg) {
    setToggle('ctrl-enabled', cfg.enabled);
    setSlider('ctrl-fps',          'val-fps',          cfg.fps          ?? 15);
    setSlider('ctrl-depth',        'val-depth',        cfg.depth        ?? 10);
    setSlider('ctrl-sat',          'val-sat',          cfg.saturation_boost ?? 1.4);
    setSlider('ctrl-ema',          'val-ema',          cfg.ema_alpha    ?? 0.35);
    setSlider('ctrl-scene-cut',    'val-scene-cut',    cfg.scene_cut    ?? 60);
    setSlider('ctrl-adap-min',     'val-adap-min',     cfg.adaptive_min ?? 3);
    setSlider('ctrl-adap-max',     'val-adap-max',     cfg.adaptive_max ?? 20);

    const capSel = document.getElementById('ctrl-capturer');
    if (capSel) capSel.value = cfg.capturer ?? 'auto';

    const stratSel = document.getElementById('ctrl-strategy');
    if (stratSel) {
        stratSel.value = cfg.strategy ?? 'adaptive_smooth';
        updateStrategyVisibility(stratSel.value);
    }
}

function setToggle(id, value) {
    const el = document.getElementById(id);
    if (el) el.checked = !!value;
}

function setSlider(inputId, spanId, value) {
    const el = document.getElementById(inputId);
    if (el) el.value = value;
    const sp = document.getElementById(spanId);
    if (sp) sp.textContent = value;
}

// ── Live controls ─────────────────────────────────────────────────────────────

function liveUpdate(key, value, spanId) {
    if (spanId) document.getElementById(spanId).textContent = value;
    _cfg[key] = value;
    api('set_ambilight_config', { [key]: value });
}

function toggleEnabled(checked) {
    _cfg.enabled = checked;
    api('set_ambilight_config', { enabled: checked });
    updateStatusBadge(checked ? null : false);
}

async function testIdle() {
    const btn = document.getElementById('btn-test-idle');
    if (btn) btn.disabled = true;
    const r = await api('test_ambilight_idle');
    if (btn) btn.disabled = false;

    const t = (key, fallback) => window.i18n.get(key) || fallback;
    if (!r.ok) {
        showNotification(t('ambilight.test_idle_error', 'Idle test failed') + (r.error ? `: ${r.error}` : ''), 'error');
    } else if (!r.enabled) {
        showNotification(t('ambilight.test_idle_disabled', 'Effects stopped, but the ambilight is disabled: enable it to see the idle state.'), 'warning');
    } else if (r.active_devices === 0) {
        showNotification(t('ambilight.test_idle_no_devices', 'Effects stopped, but no device is enabled for the ambilight.'), 'warning');
    } else {
        showNotification(t('ambilight.test_idle_ok', 'Effects stopped: the ambilight is back in control of the LEDs.'), 'success');
    }
}

function onStrategyChange(value) {
    updateStrategyVisibility(value);
    liveUpdate('strategy', value, null);
}

function updateStrategyVisibility(strategy) {
    const isAdaptive = strategy.includes('adaptive');
    const isSmooth   = strategy.includes('smooth');

    document.getElementById('group-depth').classList.toggle('hidden', isAdaptive);
    document.getElementById('group-adaptive').classList.toggle('hidden', !isAdaptive);
    document.getElementById('group-smooth').classList.toggle('hidden', !isSmooth);
}

// ── Devices ───────────────────────────────────────────────────────────────────

function renderDevices(devs, cfg) {
    const container = document.getElementById('devices-container');
    container.innerHTML = '';

    if (!devs.length) {
        container.innerHTML = `
            <div class="text-white/30 text-sm text-center py-6">
                ${window.i18n.get('ambilight.no_devices') || 'No devices available.'}<br>
                <span class="text-xs">${window.i18n.get('ambilight.no_devices_hint') || 'Connect OpenRGB and configure topologies.'}</span>
            </div>`;
        return;
    }

    const devicesCfg = cfg.devices || {};

    devs.forEach(dev => {
        const devCfg   = devicesCfg[dev.device_key] || {};
        const enabled  = devCfg.enabled ?? false;
        const zonesTxt = dev.has_topology
            ? `${dev.zone_count} ${dev.zone_count !== 1 ? (window.i18n.get('ambilight.zone_plural') || 'zones') : (window.i18n.get('ambilight.zone_singular') || 'zone')}`
            : `<span class="text-amber-400">${window.i18n.get('ambilight.no_topology') || 'no topology'}</span>`;

        const card = document.createElement('div');
        card.className = 'sci-fi-border rounded p-4 border border-white/10 space-y-3';
        card.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-bold text-sm text-white/90">${dev.name}</div>
                    <div class="text-xs text-white/40 mt-0.5">
                        ${dev.led_count} LED &middot; ${dev.topology_type} &middot; ${zonesTxt}
                    </div>
                </div>
                <label class="glass-toggle-container">
                    <span class="glass-toggle-label">Ambilight</span>
                    <input type="checkbox" class="glass-toggle-input"
                        ${enabled ? 'checked' : ''}
                        ${!dev.has_topology ? 'disabled' : ''}
                        onchange="toggleDevice('${dev.device_key}', this.checked)">
                    <div class="glass-toggle-track"><div class="glass-toggle-thumb"></div></div>
                </label>
            </div>
            ${dev.has_topology && enabled ? renderZoneToggles(dev.device_key, dev, devCfg) : ''}
            ${!dev.has_topology ? `
            <div class="text-xs text-amber-400/70 border border-amber-400/20 rounded px-3 py-2">
                ${window.i18n.get('ambilight.configure_topology_hint') || 'Configure zones in the Topology Editor page to use this device.'}
            </div>` : ''}
        `;
        container.appendChild(card);
    });
}

function renderZoneToggles(deviceKey, dev, devCfg) {
    const zonesEnabled = devCfg.zones_enabled || {};
    // Zones are loaded async — placeholder that gets populated
    return `<div id="zones-${deviceKey.replace(/[^a-z0-9]/gi, '_')}"
                 class="space-y-1 pl-2 border-l border-white/10">
        <div class="text-xs text-white/30 italic">${window.i18n.get('ambilight.loading_zones') || 'Loading zones...'}</div>
    </div>`;
}

async function loadDeviceZones(deviceKey) {
    const safeId = deviceKey.replace(/[^a-z0-9]/gi, '_');
    const container = document.getElementById(`zones-${safeId}`);
    if (!container) return;

    const zones = await api('get_ambilight_device_zones', deviceKey);
    if (!zones || !zones.length) {
        container.innerHTML = `<div class="text-xs text-white/30">${window.i18n.get('ambilight.no_zones') || 'No zones detected.'}</div>`;
        return;
    }

    const cfg      = _cfg.devices?.[deviceKey] || {};
    const zonesEna = cfg.zones_enabled || {};
    // Zones are keyed by zone_index (names can repeat); legacy name keys still read.
    const isOn = z => (String(z.zone_index) in zonesEna)
        ? !!zonesEna[String(z.zone_index)]
        : zonesEna[z.name] !== false;
    const esc = t => String(t).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    const outsideLbl = window.i18n.get('ambilight.outside_screen') || 'Outside the screen';

    const rows = zones.map(z => {
        const out = !!z.outside;
        return `
        <label class="flex items-center gap-2 py-0.5 ${out ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}">
            <input type="checkbox" ${isOn(z) && !out ? 'checked' : ''} ${out ? 'disabled' : ''}
                class="w-3 h-3" style="accent-color: var(--primary-accent);"
                onchange="toggleZone('${deviceKey}', ${Number(z.zone_index)}, this.checked)">
            <span class="text-xs text-white/60 flex-1">${esc(z.name)}</span>
            <span class="text-xs text-white/30">${out ? esc(outsideLbl) : esc(z.edge)}</span>
        </label>`;
    }).join('');

    const onScreen = zones.some(z => !z.outside);
    const warn = onScreen ? '' : `
        <div class="text-xs text-amber-400/70 border border-amber-400/20 rounded px-3 py-2 mb-1">
            ${esc(window.i18n.get('ambilight.no_zone_on_screen') || 'No zone is on the screen yet: place the screen rectangle in the Topology Editor.')}
        </div>`;
    container.innerHTML = warn + rows;
}

function toggleDevice(deviceKey, enabled) {
    api('set_ambilight_device_enabled', deviceKey, enabled);
    if (!_cfg.devices) _cfg.devices = {};
    if (!_cfg.devices[deviceKey]) _cfg.devices[deviceKey] = {};
    _cfg.devices[deviceKey].enabled = enabled;
    // Re-render to show/hide zone toggles
    renderDevices(_devs, _cfg);
    if (enabled) {
        setTimeout(() => loadDeviceZones(deviceKey), 50);
    }
}

function toggleZone(deviceKey, zoneIndex, enabled) {
    api('set_ambilight_zone_enabled', deviceKey, zoneIndex, enabled);
    if (!_cfg.devices) _cfg.devices = {};
    if (!_cfg.devices[deviceKey]) _cfg.devices[deviceKey] = {};
    if (!_cfg.devices[deviceKey].zones_enabled) _cfg.devices[deviceKey].zones_enabled = {};
    _cfg.devices[deviceKey].zones_enabled[String(zoneIndex)] = enabled;
}

// ── Status polling ────────────────────────────────────────────────────────────

async function pollStatus() {
    const s = await api('get_ambilight_status');
    if (!s) return;

    const fpsBadge = document.getElementById('fps-badge');
    if (fpsBadge) fpsBadge.textContent = s.running ? `${s.fps} fps` : '— fps';

    const capEl = document.getElementById('stat-capturer');
    if (capEl) capEl.textContent = s.capturer || '—';

    updateStatusBadge(s.enabled && s.running);
}

function updateStatusBadge(active) {
    const el = document.getElementById('status-dot');
    if (!el) return;
    if (active === null || active === undefined) return;
    el.className = active
        ? 'w-2 h-2 rounded-full bg-green-400 nav-dot-active'
        : 'w-2 h-2 rounded-full bg-white/20';
    const lbl = document.getElementById('status-label');
    if (lbl) lbl.textContent = active ? (window.i18n.get('ambilight.status_active') || 'ACTIVE') : (window.i18n.get('ambilight.status_inactive') || 'INACTIVE');
}

// ── Page init: load zone toggles for enabled devices ─────────────────────────

async function loadEnabledZones() {
    for (const dev of _devs) {
        const devCfg = (_cfg.devices || {})[dev.device_key] || {};
        if (devCfg.enabled && dev.has_topology) {
            await loadDeviceZones(dev.device_key);
        }
    }
}

window.addEventListener('load', () => {
    setTimeout(loadEnabledZones, 300);
});

// The cards may be drawn before the translations arrive (the texts would be the
// raw keys): draw them again once they are loaded.
window.addEventListener('i18nLoaded', () => {
    renderDevices(_devs, _cfg);
    loadEnabledZones();
    pollStatus();
});
