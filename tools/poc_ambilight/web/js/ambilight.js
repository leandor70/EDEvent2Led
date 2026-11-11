'use strict';

let _strategies = {};
let _zones      = [];

// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('load', async () => {
    const [strategies, config, zones] = await Promise.all([
        eel.get_strategies()(),
        eel.get_config()(),
        eel.get_zones()(),
    ]);

    _strategies = strategies;
    _zones      = zones;

    populateStrategySelect(strategies, config.strategy);
    applyConfig(config);
    buildZoneToggles(zones, config.zones_enabled);
    buildZonePreview(zones);

    setInterval(poll, 150);
});

// ── Controls sync ─────────────────────────────────────────────────────────────

function liveUpdate(key, value, valSpanId) {
    document.getElementById(valSpanId).textContent = value;
    eel.set_config({ [key]: value });
}

function applyConfig(cfg) {
    setSlider('ctrl-fps',          'val-fps',          cfg.fps);
    setSlider('ctrl-depth',        'val-depth',        cfg.depth);
    setSlider('ctrl-ema-alpha',    'val-ema-alpha',    cfg.ema_alpha);
    setSlider('ctrl-scene-cut',    'val-scene-cut',    cfg.scene_cut);
    setSlider('ctrl-saturation',   'val-saturation',   cfg.saturation_boost);
    setSlider('ctrl-adaptive-min', 'val-adaptive-min', cfg.adaptive_min);
    setSlider('ctrl-adaptive-max', 'val-adaptive-max', cfg.adaptive_max);
    document.getElementById('ctrl-preview').checked = cfg.preview_only;
    updateStrategyVisibility(cfg.strategy);
}

function setSlider(inputId, spanId, value) {
    const el = document.getElementById(inputId);
    if (!el) return;
    el.value = value;
    document.getElementById(spanId).textContent = value;
}

// ── Strategy select ───────────────────────────────────────────────────────────

function populateStrategySelect(strategies, current) {
    const sel = document.getElementById('ctrl-strategy');
    for (const [key, desc] of Object.entries(strategies)) {
        const opt = document.createElement('option');
        opt.value       = key;
        opt.textContent = key;
        sel.appendChild(opt);
    }
    sel.value = current;
    showStrategyDesc(current);

    sel.addEventListener('change', () => {
        showStrategyDesc(sel.value);
        updateStrategyVisibility(sel.value);
        eel.set_config({ strategy: sel.value });
    });
}

function showStrategyDesc(key) {
    const full = _strategies[key] || '';
    const desc = full.includes('—') ? full.split('—')[1].trim() : full;
    document.getElementById('strategy-desc').textContent = desc;
}

function updateStrategyVisibility(strategy) {
    const isAdaptive = strategy.includes('adaptive');
    const isSmooth   = strategy.includes('smooth');
    const isHsv      = strategy === 'hsv';

    document.getElementById('group-depth').classList.toggle('hidden', isAdaptive);
    document.getElementById('group-adaptive').classList.toggle('hidden', !isAdaptive);
    document.getElementById('group-smooth').classList.toggle('hidden', !isSmooth);
    // Boost sat non si applica a hsv — visivamente lo dimmo
    document.getElementById('group-saturation').style.opacity = isHsv ? '0.35' : '1';
    const sat = document.getElementById('ctrl-saturation');
    if (sat) sat.disabled = isHsv;
}

// ── Zone toggles ──────────────────────────────────────────────────────────────

function buildZoneToggles(zones, enabledMap) {
    const container = document.getElementById('zone-toggles');
    container.innerHTML = '';
    for (const zone of zones) {
        const enabled = enabledMap[zone.name] !== false;
        const label   = document.createElement('label');
        label.className = 'flex items-center gap-2 cursor-pointer';
        label.innerHTML = `
            <input type="checkbox" ${enabled ? 'checked' : ''}
                class="accent-sky-400 w-3 h-3"
                onchange="toggleZone('${zone.name}', this.checked)">
            <span class="text-gray-300 flex-1">${zone.name}</span>
            <span class="text-gray-600">${zone.led_count} LED &middot; ${zone.edge}</span>
        `;
        container.appendChild(label);
    }
}

function toggleZone(name, enabled) {
    eel.get_config()(cfg => {
        const zones_enabled = Object.assign({}, cfg.zones_enabled, { [name]: enabled });
        eel.set_config({ zones_enabled });
    });
}

// ── Zone LED preview ──────────────────────────────────────────────────────────

function buildZonePreview(zones) {
    const container = document.getElementById('zone-preview');
    container.innerHTML = '';
    for (const zone of zones) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div class="flex justify-between mb-1">
                <span class="text-gray-400">${zone.name}</span>
                <span class="text-gray-600">${zone.led_count} LED &middot; ${zone.edge}</span>
            </div>
            <div id="strip-${zone.name}" class="led-strip bg-panel">
                ${Array(zone.led_count).fill('<div class="led-cell" style="background:#1a1f2a"></div>').join('')}
            </div>
        `;
        container.appendChild(wrapper);
    }
}

function updateZonePreview(zoneColors) {
    for (const [name, colors] of Object.entries(zoneColors)) {
        const strip = document.getElementById(`strip-${name}`);
        if (!strip) continue;
        const cells = strip.children;
        const n     = Math.min(cells.length, colors.length);
        for (let i = 0; i < n; i++) {
            const [r, g, b] = colors[i];
            cells[i].style.backgroundColor = `rgb(${r},${g},${b})`;
        }
    }
}

// ── Polling ───────────────────────────────────────────────────────────────────

async function poll() {
    const s = await eel.get_status()();

    const fpsBadge = document.getElementById('fps-badge');
    fpsBadge.textContent = s.running ? `${s.actual_fps} fps` : '— fps';

    document.getElementById('stat-fps').textContent    = s.running ? s.actual_fps : '—';
    document.getElementById('stat-frames').textContent = s.running ? s.frame_count : '—';

    const statusEl = document.getElementById('stat-status');
    if (s.running) {
        statusEl.textContent  = 'RUN';
        statusEl.className    = 'text-xl font-bold text-green-400';
    } else {
        statusEl.textContent  = 'IDLE';
        statusEl.className    = 'text-xl font-bold text-gray-600';
    }

    document.getElementById('btn-start').disabled = s.running;
    document.getElementById('btn-stop').disabled  = !s.running;

    const cap = document.getElementById('stat-capturer');
    if (cap) cap.textContent = s.capturer || '—';

    if (s.zone_colors && Object.keys(s.zone_colors).length)
        updateZonePreview(s.zone_colors);
}

// ── Commands ──────────────────────────────────────────────────────────────────

async function cmdStart() {
    const r = await eel.start_capture()();
    if (r && !r.ok) console.warn('Start:', r.msg);
}

async function cmdStop() {
    await eel.stop_capture()();
}
