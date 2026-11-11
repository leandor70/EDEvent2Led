/**
 * Events Mapper — split-pane, inline effect editor (v3).
 *
 * Left panel: filterable event list.
 * Right panel: EffectEditorModule for inline step editing.
 * Effects are stored inline in event_mappings.json (no library references).
 */

// ── State ─────────────────────────────────────────────────────────────────────

let availableEvents = [];          // [{name, category, description, importance}]
let eventMappings = new Map();     // event_name → {priority, enabled, effect, effect_name}

let selectedEventName = null;
let currentEventEffect = null;     // in-memory (may differ from saved)
let savedEventEffect = null;       // snapshot at last save (for revert)
let _isDirty = false;

let _editorModule = null;          // EffectEditorModule instance
let _allTemplates = [];            // cached from get_effect_templates()

// Filter state
let currentCategory = 'all';
let searchQuery = '';
let mappingFilter = 'all';
let minImportance = 0;


// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async function () {
    console.log('[Events] Initializing...');

    await loadUserSettings();

    await Promise.all([loadAvailableEvents(), loadEventMappings()]);

    _editorModule = new EffectEditorModule({
        stepsContainerId: 'steps-container',
        timelineCanvasId: null,   // delegate to page-level renderColorTimeline()
        onStepsChange: (steps) => {
            if (currentEventEffect && typeof currentEventEffect === 'object') {
                currentEventEffect.steps = steps;
            }
            markDirty();
        },
    });
    await _editorModule.init();

    renderEventsList();
    setupFilterListeners();
    setupEditorListeners();
    setupDeassignListeners();

    console.log('[Events] Ready —', availableEvents.length, 'events,', eventMappings.size, 'mappings');
});


// ── Settings / i18n ──────────────────────────────────────────────────────────

async function loadUserSettings() {
    const result = await api('get_settings');
    if (result?.language && window.i18n) await window.i18n.init(result.language);
    requestAnimationFrame(() => document.body.classList.add('loaded'));
}


// ── Data loading ──────────────────────────────────────────────────────────────

async function loadAvailableEvents() {
    const result = await api('get_available_events');
    if (!result?.success) { showNotification(window.i18n.get('notifications.failed_load_events') || 'Failed to load events', 'error'); return; }
    availableEvents = result.events || [];
}

async function loadEventMappings() {
    const result = await api('get_event_mappings');
    if (!result?.success) { showNotification(window.i18n.get('notifications.failed_load_mappings') || 'Failed to load mappings', 'error'); return; }
    eventMappings = new Map(
        (result.mappings || []).map(m => [m.event_name, m])
    );
}


// ── Filter helpers ────────────────────────────────────────────────────────────

function getFilteredEvents() {
    let pairs = availableEvents.map(ev => ({
        event: ev,
        mapping: eventMappings.get(ev.name) || null,
    }));

    if (currentCategory !== 'all')
        pairs = pairs.filter(({ event }) => event.category === currentCategory);

    if (searchQuery)
        pairs = pairs.filter(({ event }) =>
            event.name.toLowerCase().includes(searchQuery) ||
            (event.description || '').toLowerCase().includes(searchQuery)
        );

    if (minImportance > 0)
        pairs = pairs.filter(({ event }) => (event.importance || 0) >= minImportance);

    if (mappingFilter === 'mapped')
        pairs = pairs.filter(({ mapping }) => mapping?.effect !== undefined && mapping?.effect !== null);
    else if (mappingFilter === 'unmapped')
        pairs = pairs.filter(({ mapping }) => !mapping || mapping.effect == null);

    return pairs;
}


// ── Render event list ─────────────────────────────────────────────────────────

function renderEventsList() {
    const container = document.getElementById('events-list');
    if (!container) return;

    const pairs = getFilteredEvents();
    const mapped = pairs.filter(({ mapping }) => mapping?.effect != null).length;

    document.getElementById('count-mapped').textContent = mapped;
    document.getElementById('count-total').textContent = pairs.length;

    if (pairs.length === 0) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center py-12 text-white/25 text-sm">
                <span class="material-symbols-outlined text-4xl mb-3">search_off</span>
                No events match the current filters
            </div>`;
        return;
    }

    container.innerHTML = '';
    pairs.forEach(({ event, mapping }) => {
        container.appendChild(createEventRow(event, mapping));
    });
}

const CATEGORY_COLORS = {
    'Startup':          'text-slate-400',
    'Travel':           'text-blue-400',
    'Combat':           'text-red-400',
    'Exploration':      'text-green-400',
    'Trade':            'text-yellow-400',
    'Station Services': 'text-purple-400',
    'Powerplay':        'text-orange-400',
    'Squadrons':        'text-indigo-400',
    'Fleet Carriers':   'text-teal-400',
    'Odyssey':          'text-cyan-400',
    'Other Events':     'text-gray-400',
};

function effectDotClass(effect) {
    if (effect && typeof effect === 'object') return 'bg-[var(--primary-accent)]';
    if (effect === 'keyboard_default') return 'bg-cyan-400';
    return 'bg-white/15';
}

function createEventRow(event, mapping) {
    const effect = mapping?.effect ?? null;
    const isSelected = event.name === selectedEventName;
    const hasMeta = mapping && (mapping.effect !== undefined);
    const priority = mapping?.priority ?? 5;
    const enabled = mapping?.enabled !== false;
    const catColor = CATEGORY_COLORS[event.category] || 'text-gray-400';

    const div = document.createElement('div');
    div.className = `event-row px-4 py-2.5 flex items-center gap-3${isSelected ? ' selected' : ''}`;
    div.dataset.eventName = event.name;

    div.innerHTML = `
        <!-- Effect indicator dot -->
        <span class="w-2 h-2 rounded-full flex-shrink-0 ${effectDotClass(effect)}"></span>
        <!-- Event name + description + category -->
        <div class="flex-1 min-w-0">
            <div class="font-mono text-sm ${hasMeta ? 'text-white' : 'text-white/45'} truncate">${escapeHtml(event.name)}</div>
            ${event.description ? `<div class="text-xs text-white/40 truncate leading-tight">${escapeHtml(event.description)}</div>` : ''}
            ${event.category ? `<div class="text-xs ${catColor} opacity-80">${escapeHtml(event.category)}</div>` : ''}
        </div>
        <!-- Priority badge (only when mapped) -->
        ${hasMeta ? `<span class="text-xs font-mono text-white/50 shrink-0">P${priority}</span>` : ''}
        <!-- Enabled toggle (only when mapped) -->
        ${hasMeta ? `
        <label class="glass-toggle-container shrink-0" title="${enabled ? 'Enabled' : 'Disabled'}" onclick="event.stopPropagation()">
            <input type="checkbox" class="glass-toggle-input ev-enabled-toggle"
                data-event="${escapeAttr(event.name)}" ${enabled ? 'checked' : ''}>
            <div class="glass-toggle-track" style="transform:scale(0.75);transform-origin:right center;">
                <div class="glass-toggle-thumb"></div>
            </div>
        </label>` : ''}
    `;

    div.addEventListener('click', () => selectEvent(event.name));

    // Enabled toggle inline (doesn't navigate)
    const toggle = div.querySelector('.ev-enabled-toggle');
    if (toggle) {
        toggle.addEventListener('change', async (e) => {
            await toggleMapping(event.name, e.target.checked);
        });
    }

    return div;
}


// ── Event selection ───────────────────────────────────────────────────────────

async function selectEvent(eventName) {
    if (_isDirty && selectedEventName && selectedEventName !== eventName) {
        markClean();
    }

    selectedEventName = eventName;
    renderEventsList(); // update selected highlight

    const mapping = eventMappings.get(eventName) || null;
    const effect = mapping?.effect ?? null;

    // Update editor header
    const nameEl = document.getElementById('editor-event-name');
    const descEl = document.getElementById('editor-event-desc');
    const ctrlEl = document.getElementById('editor-controls');
    const priorityEl = document.getElementById('editor-priority');
    const priorityValEl = document.getElementById('editor-priority-value');
    const enabledEl = document.getElementById('editor-enabled');

    if (nameEl) nameEl.textContent = eventName;

    const eventDef = availableEvents.find(e => e.name === eventName);
    if (descEl && eventDef?.description) {
        descEl.textContent = eventDef.description;
        descEl.classList.remove('hidden');
    } else if (descEl) {
        descEl.classList.add('hidden');
    }

    if (ctrlEl && mapping) {
        ctrlEl.classList.remove('hidden');
        if (priorityEl) priorityEl.value = mapping.priority ?? 5;
        if (priorityValEl) priorityValEl.textContent = mapping.priority ?? 5;
        if (enabledEl) enabledEl.checked = mapping.enabled !== false;
    } else if (ctrlEl) {
        // Default controls for unmapped events
        ctrlEl.classList.remove('hidden');
        if (priorityEl) priorityEl.value = 5;
        if (priorityValEl) priorityValEl.textContent = 5;
        if (enabledEl) enabledEl.checked = true;
    }

    // Snapshot saved state
    savedEventEffect = deepClone(effect);
    currentEventEffect = deepClone(effect);

    // Show appropriate panel
    showEditorActions(true);

    if (typeof effect === 'object' && effect !== null) {
        await showEffectEditor(effect);
    } else if (effect === 'keyboard_default') {
        showPanel('keyboard-default-panel');
        showStepActions(false);
    } else {
        showPanel('no-effect-panel');
        showStepActions(false);
    }
}

async function showEffectEditor(effectData) {
    showPanel('effect-editor-content');
    showStepActions(true);

    const nameInput = document.getElementById('editor-effect-name');
    if (nameInput) nameInput.value = effectData?.name || '';

    if (_editorModule) {
        await _editorModule.loadEffect(effectData);
    }
}

function showPanel(panelId) {
    ['empty-effect-panel', 'no-effect-panel', 'keyboard-default-panel', 'effect-editor-content']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.toggle('hidden', id !== panelId);
            if (el && id !== panelId) el.classList.add('hidden');
            if (el && id === panelId) el.classList.remove('hidden');
        });
}

function showEditorActions(visible) {
    const el = document.getElementById('editor-actions');
    if (el) el.classList.toggle('hidden', !visible);
}

function showStepActions(visible) {
    const el = document.getElementById('step-actions');
    if (el) el.classList.toggle('hidden', !visible);
}


// ── Save / Revert ─────────────────────────────────────────────────────────────

async function saveCurrentEffect() {
    if (!selectedEventName) return;

    let effectToSave = currentEventEffect;

    // If effect editor is active, read current steps + name
    if (!document.getElementById('effect-editor-content')?.classList.contains('hidden') && _editorModule) {
        const steps = _editorModule.getSteps();
        const nameInput = document.getElementById('editor-effect-name');
        if (typeof effectToSave === 'object' && effectToSave !== null) {
            effectToSave = { ...effectToSave, steps };
            if (nameInput?.value.trim()) effectToSave.name = nameInput.value.trim();
        } else {
            effectToSave = buildEffectDict(selectedEventName, steps);
        }
        currentEventEffect = effectToSave;
    }

    const priority = parseInt(document.getElementById('editor-priority')?.value || '5', 10);
    const enabled = document.getElementById('editor-enabled')?.checked !== false;

    // Save effect inline
    const r1 = await api('save_event_effect', selectedEventName, effectToSave);
    if (!r1?.success) {
        showNotification(window.i18n.interpolate('notifications.save_failed_event', {error: r1?.error || 'Unknown error'}) || `Save failed: ${r1?.error || 'Unknown error'}`, 'error');
        return;
    }

    // Save meta (priority / enabled)
    await api('update_event_mapping', selectedEventName, { priority, enabled });

    // Update local state
    const existing = eventMappings.get(selectedEventName) || {};
    eventMappings.set(selectedEventName, {
        ...existing,
        event_name: selectedEventName,
        effect: effectToSave,
        effect_name: typeof effectToSave === 'object' && effectToSave !== null
            ? (effectToSave.name || 'Unnamed')
            : (effectToSave === 'keyboard_default' ? 'Keyboard Default' : null),
        priority,
        enabled,
    });

    savedEventEffect = deepClone(effectToSave);
    markClean();
    renderEventsList();
    showNotification(window.i18n.interpolate('notifications.saved_event_name', {event: selectedEventName}) || `Saved: ${selectedEventName}`, 'success');
}

function revertEffect() {
    if (!selectedEventName) return;
    if (!confirm('Discard changes and revert to last saved state?')) return;

    currentEventEffect = deepClone(savedEventEffect);

    if (typeof currentEventEffect === 'object' && currentEventEffect !== null) {
        showEffectEditor(currentEventEffect);
    } else if (currentEventEffect === 'keyboard_default') {
        showPanel('keyboard-default-panel');
        showStepActions(false);
    } else {
        showPanel('no-effect-panel');
        showStepActions(false);
    }
    markClean();
}


// ── Effect type actions ───────────────────────────────────────────────────────

function createNewEffect() {
    if (!selectedEventName) return;
    const newEffect = buildEffectDict(selectedEventName, []);
    currentEventEffect = newEffect;
    showEffectEditor(newEffect);
    showStepActions(true);
    showEditorActions(true);
    markDirty();
}

function buildEffectDict(eventName, steps = []) {
    return {
        name: eventName,
        steps,
        topology_support: ['1D', '2D'],
        post_behavior: 'static_color',
        post_behavior_data: null,
        category: 'event',
        metadata: {},
    };
}

function setEffectNull() {
    if (!selectedEventName) return;
    currentEventEffect = null;
    showPanel('no-effect-panel');
    showStepActions(false);
    markDirty();
}

function setEffectKeyboardDefault() {
    if (!selectedEventName) return;
    currentEventEffect = 'keyboard_default';
    showPanel('keyboard-default-panel');
    showStepActions(false);
    markDirty();
}

function addEditorStep() {
    if (_editorModule) _editorModule.addStep();
}

function addKeyboardStep() {
    if (!_editorModule) return;
    const steps = _editorModule.getSteps();
    const lastStep = steps.at(-1);
    if (lastStep?.effect_type === 'keyboard_default') {
        showNotification(window.i18n.get('common.keyboard_default_is_last') || 'Last step is already Keyboard Default', 'info');
        return;
    }
    _editorModule.addStep('keyboard_default');
}

async function testCurrentEffect() {
    if (!selectedEventName) return;

    let effectData = currentEventEffect;

    if (!document.getElementById('effect-editor-content')?.classList.contains('hidden') && _editorModule) {
        const steps = _editorModule.getSteps();
        effectData = typeof currentEventEffect === 'object' && currentEventEffect
            ? { ...currentEventEffect, steps }
            : buildEffectDict(selectedEventName, steps);
    }

    if (!effectData || typeof effectData !== 'object') {
        showNotification(window.i18n.get('notifications.no_effect_to_test') || 'No effect to test', 'warning');
        return;
    }

    showNotification(window.i18n.get('notifications.testing_effect_short') || 'Testing effect...', 'info');
    const result = await api('test_event_effect_live', selectedEventName, effectData);
    if (!result?.success) showNotification(window.i18n.interpolate('notifications.save_failed_event', {error: result?.error || 'Unknown'}) || `Test failed: ${result?.error || 'Unknown'}`, 'error');
    else showNotification(window.i18n.get('notifications.effect_playing_hardware') || 'Effect playing on hardware', 'success');
}

async function stopEffect() {
    await api('stop_current_effect');
    showNotification(window.i18n.get('notifications.effects_stopped') || 'Effects stopped', 'info');
}


// ── Dirty state ───────────────────────────────────────────────────────────────

function _updateTimelineLabels(steps) {
    // called by onStepsChange — renderColorTimeline also updates these, but this handles
    // the case where the canvas is not yet visible (e.g. first load before panel switch)
    const total = Array.isArray(steps)
        ? steps.reduce((s, st) => s + (st?.params?.duration_ms || st?.duration || 0), 0)
        : 0;
    const fmt = ms => ms >= 1000 ? (ms / 1000).toFixed(1) + 's' : ms + 'ms';
    const totalEl = document.getElementById('totalDuration');
    const endEl   = document.getElementById('endTime');
    if (totalEl) totalEl.textContent = (window.i18n.get('status_strings.total_prefix') || 'Total: ') + fmt(total);
    if (endEl)   endEl.textContent   = fmt(total);
}

// ── Color Timeline (rich renderer — same visual as effects-editor) ─────────────

function _drawBreathSegment(ctx, x, y, w, h, c1, c2, loops) {
    const n = Math.max(1, loops || 1);
    const cw = w / n;
    for (let i = 0; i < n; i++) {
        const cx = x + i * cw, half = cw / 2;
        const g1 = ctx.createLinearGradient(cx, y, cx + half, y);
        g1.addColorStop(0, c1); g1.addColorStop(1, c2);
        ctx.fillStyle = g1; ctx.fillRect(cx, y, half, h);
        const g2 = ctx.createLinearGradient(cx + half, y, cx + cw, y);
        g2.addColorStop(0, c2); g2.addColorStop(1, c1);
        ctx.fillStyle = g2; ctx.fillRect(cx + half, y, half, h);
    }
}

function _drawColorCycleSegment(ctx, x, y, w, h, colors) {
    const sw = w / colors.length;
    colors.forEach((c, i) => {
        const g = ctx.createLinearGradient(x + i * sw, y, x + (i + 1) * sw, y);
        g.addColorStop(0, c); g.addColorStop(0.7, c); g.addColorStop(1, colors[(i + 1) % colors.length]);
        ctx.fillStyle = g; ctx.fillRect(x + i * sw, y, sw, h);
    });
}

function _drawSpatialSegment(ctx, x, y, w, h, colors, layout) {
    if (layout === 'horizontal') {
        const bh = h / colors.length;
        colors.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(x, y + i * bh, w, bh); });
    } else if (layout === 'vertical') {
        const bw = w / colors.length;
        colors.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(x + i * bw, y, bw, h); });
    } else if (layout === 'grid' && colors.length >= 4) {
        const hw = w / 2, hh = h / 2;
        ctx.fillStyle = colors[0]; ctx.fillRect(x,      y,      hw, hh);
        ctx.fillStyle = colors[1]; ctx.fillRect(x + hw, y,      hw, hh);
        ctx.fillStyle = colors[2]; ctx.fillRect(x,      y + hh, hw, hh);
        ctx.fillStyle = colors[3]; ctx.fillRect(x + hw, y + hh, hw, hh);
    }
}

function renderColorTimeline() {
    const canvas = document.getElementById('colorTimeline');
    if (!canvas) return;

    const ctx    = canvas.getContext('2d');
    const width  = canvas.width = canvas.offsetWidth;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    // Collect steps from DOM
    const steps = [];
    document.querySelectorAll('#steps-container .step-card').forEach((card, idx) => {
        const durationInput = card.querySelector('.step-duration');
        const colorInputs   = card.querySelectorAll('.step-color');
        const effectSelect  = card.querySelector('.step-type');
        if (!durationInput || colorInputs.length === 0) return;
        const colors = Array.from(colorInputs).map(inp =>
            (inp.value && inp.value.startsWith('#')) ? inp.value : '#0055FF'
        );
        const numLoopsInput = card.querySelector('.param-num-loops');
        steps.push({
            duration:   parseInt(durationInput.value) || 500,
            colors,
            effectType: effectSelect ? effectSelect.value : 'static_transition',
            numLoops:   numLoopsInput ? parseInt(numLoopsInput.value) || 1 : 1,
            name:       effectSelect?.options[effectSelect.selectedIndex]?.text || 'Effect',
            index:      idx + 1,
        });
    });

    if (steps.length === 0) return;

    const totalDuration = steps.reduce((s, st) => s + st.duration, 0);

    // Update labels
    const fmt = ms => ms >= 1000 ? (ms / 1000).toFixed(1) + 's' : ms + 'ms';
    const totalEl = document.getElementById('totalDuration');
    const endEl   = document.getElementById('endTime');
    if (totalEl) totalEl.textContent = (window.i18n.get('status_strings.total_prefix') || 'Total: ') + fmt(totalDuration);
    if (endEl)   endEl.textContent   = fmt(totalDuration);

    const padding      = 20;
    const timelineH    = 60;
    const timelineY    = 20;
    const labelY       = timelineY + timelineH + 15;

    // Background
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.fillRect(padding, timelineY, width - padding * 2, timelineH);

    // Step segments
    let currentX = padding;
    steps.forEach((step, idx) => {
        const sw = ((width - padding * 2) * step.duration) / totalDuration;
        const prevColor = idx > 0 ? steps[idx - 1].colors[0] : '#000000';

        switch (step.effectType) {
            case 'breath':
                step.colors.length >= 2
                    ? _drawBreathSegment(ctx, currentX, timelineY, sw, timelineH, step.colors[0], step.colors[1], step.numLoops)
                    : (ctx.fillStyle = step.colors[0], ctx.fillRect(currentX, timelineY, sw, timelineH));
                break;
            case 'color_cycle':
                step.colors.length >= 2
                    ? _drawColorCycleSegment(ctx, currentX, timelineY, sw, timelineH, step.colors)
                    : (ctx.fillStyle = step.colors[0], ctx.fillRect(currentX, timelineY, sw, timelineH));
                break;
            case 'static_transition': {
                const g = ctx.createLinearGradient(currentX, timelineY, currentX + sw, timelineY);
                g.addColorStop(0, prevColor); g.addColorStop(1, step.colors[0]);
                ctx.fillStyle = g; ctx.fillRect(currentX, timelineY, sw, timelineH);
                break;
            }
            case 'four_corner_nuance':
                step.colors.length >= 4
                    ? _drawSpatialSegment(ctx, currentX, timelineY, sw, timelineH, step.colors, 'grid')
                    : (ctx.fillStyle = step.colors[0], ctx.fillRect(currentX, timelineY, sw, timelineH));
                break;
            case 'wave': case 'bump': {
                if (step.colors.length >= 2) {
                    const half = sw / 2;
                    const g1 = ctx.createLinearGradient(currentX, 0, currentX + half, 0);
                    g1.addColorStop(0, step.colors[0]); g1.addColorStop(1, step.colors[1]);
                    ctx.fillStyle = g1; ctx.fillRect(currentX, timelineY, half, timelineH);
                    const g2 = ctx.createLinearGradient(currentX + half, 0, currentX + sw, 0);
                    g2.addColorStop(0, step.effectType === 'bump' ? step.colors[1] : step.colors[1]);
                    g2.addColorStop(1, step.effectType === 'bump' ? step.colors[0] : step.colors[0]);
                    ctx.fillStyle = g2; ctx.fillRect(currentX + half, timelineY, half, timelineH);
                } else {
                    ctx.fillStyle = step.colors[0]; ctx.fillRect(currentX, timelineY, sw, timelineH);
                }
                break;
            }
            default:
                step.colors.length >= 2
                    ? _drawSpatialSegment(ctx, currentX, timelineY, sw, timelineH, step.colors, 'horizontal')
                    : (ctx.fillStyle = step.colors[0], ctx.fillRect(currentX, timelineY, sw, timelineH));
                break;
        }

        // Step label
        ctx.font = '10px Orbitron, monospace';
        ctx.textAlign = 'center';
        const lx = currentX + sw / 2;
        ctx.fillStyle = '#FF6600';
        ctx.fillText('Step ' + step.index, lx, labelY);
        ctx.fillStyle = 'rgba(255,255,255,0.6)';
        ctx.font = '9px Rajdhani, sans-serif';
        ctx.fillText(fmt(step.duration), lx, labelY + 12);

        currentX += sw;
    });

    // Step boundary markers + time labels
    currentX = padding;
    let cumTime = 0;
    steps.forEach((step, idx) => {
        const sw = ((width - padding * 2) * step.duration) / totalDuration;
        if (idx > 0) {
            ctx.strokeStyle = 'rgba(255,102,0,0.5)';
            ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
            ctx.beginPath(); ctx.moveTo(currentX, timelineY); ctx.lineTo(currentX, timelineY + timelineH); ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#FF6600'; ctx.font = 'bold 9px Rajdhani, sans-serif'; ctx.textAlign = 'center';
            ctx.fillText(fmt(cumTime), currentX, timelineY - 5);
        }
        currentX += sw; cumTime += step.duration;
    });

    // Intermediate tick marks
    const tw = width - padding * 2;
    const tickInterval = totalDuration <= 2000 ? 250 : totalDuration <= 5000 ? 500 : 1000;
    ctx.strokeStyle = 'rgba(255,255,255,0.4)'; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
    for (let t = tickInterval; t < totalDuration; t += tickInterval) {
        const tx = padding + (tw * t / totalDuration);
        let tooClose = false; let ct = 0;
        for (const st of steps) {
            ct += st.duration;
            if (Math.abs(tx - (padding + tw * ct / totalDuration)) < 15) { tooClose = true; break; }
        }
        if (!tooClose) {
            ctx.beginPath(); ctx.moveTo(tx, timelineY + timelineH * 0.2); ctx.lineTo(tx, timelineY + timelineH * 0.8); ctx.stroke();
            if (t % 1000 === 0) {
                ctx.fillStyle = 'rgba(255,255,255,0.3)'; ctx.font = '8px Rajdhani, sans-serif'; ctx.textAlign = 'center';
                ctx.fillText((t / 1000).toFixed(1) + 's', tx, timelineY + timelineH + 8);
            }
        }
    }
    ctx.setLineDash([]);

    // Outer border + sci-fi corner accents
    ctx.strokeStyle = 'rgba(255,102,0,0.3)'; ctx.lineWidth = 1;
    ctx.strokeRect(padding, timelineY, width - padding * 2, timelineH);
    const cs = 8;
    ctx.strokeStyle = '#FF6600'; ctx.lineWidth = 2;
    [[padding, timelineY + cs, padding, timelineY, padding + cs, timelineY],
     [width - padding - cs, timelineY, width - padding, timelineY, width - padding, timelineY + cs],
     [padding, timelineY + timelineH - cs, padding, timelineY + timelineH, padding + cs, timelineY + timelineH],
     [width - padding - cs, timelineY + timelineH, width - padding, timelineY + timelineH, width - padding, timelineY + timelineH - cs]
    ].forEach(([x1, y1, x2, y2, x3, y3]) => {
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.lineTo(x3, y3); ctx.stroke();
    });
}

function markDirty() {
    _isDirty = true;
    document.getElementById('dirty-dot')?.classList.remove('hidden');
}

function markClean() {
    _isDirty = false;
    document.getElementById('dirty-dot')?.classList.add('hidden');
}


// ── Template modal ────────────────────────────────────────────────────────────

async function openTemplateModal() {
    if (_allTemplates.length === 0) {
        const result = await api('get_effect_templates');
        _allTemplates = result?.templates || [];
    }
    renderTemplateList(_allTemplates);
    document.getElementById('template-modal')?.classList.remove('hidden');
    document.getElementById('template-search')?.focus();
}

function closeTemplateModal() {
    document.getElementById('template-modal')?.classList.add('hidden');
}

function renderTemplateList(templates) {
    const container = document.getElementById('template-list');
    if (!container) return;
    if (templates.length === 0) {
        container.innerHTML = `<div class="text-center text-white/30 py-8 text-sm">${window.i18n.get('notifications.no_templates_found_text') || 'No templates found'}</div>`;
        return;
    }
    container.innerHTML = '';
    templates.forEach(tmpl => {
        const div = document.createElement('div');
        div.className = 'template-card';

        const stepsCount = tmpl.steps?.length || 0;
        const catColors = tmpl.steps?.slice(0, 5).map(s => {
            const c = s.params?.colors?.[0];
            return c ? `rgb(${c[0]},${c[1]},${c[2]})` : null;
        }).filter(Boolean) || [];

        div.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="flex gap-1 flex-shrink-0">
                    ${catColors.map(c => `<span class="w-3 h-3 rounded-full" style="background:${c}"></span>`).join('')}
                    ${!catColors.length ? '<span class="w-3 h-3 rounded-full bg-white/20"></span>' : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm text-white/80 font-medium truncate">${escapeHtml(tmpl._template_name || tmpl.name || 'Unnamed')}</div>
                    <div class="text-xs text-white/50">${stepsCount} step${stepsCount !== 1 ? 's' : ''}</div>
                </div>
                <span class="material-symbols-outlined text-white/25 text-sm">download</span>
            </div>`;

        div.addEventListener('click', () => importTemplate(tmpl));
        container.appendChild(div);
    });
}

async function importTemplate(templateData) {
    const clean = { ...templateData };
    delete clean._template_id;
    delete clean._template_name;

    currentEventEffect = deepClone(clean);
    await showEffectEditor(currentEventEffect);
    showStepActions(true);
    closeTemplateModal();
    markDirty();
    showNotification(window.i18n.interpolate('notifications.template_imported', {name: clean.name || 'Unnamed'}) || `Template imported: ${clean.name || 'Unnamed'}`, 'success');
}


// ── Mapping operations ────────────────────────────────────────────────────────

async function toggleMapping(eventName, newEnabled) {
    const result = await api('update_event_mapping', eventName, { enabled: newEnabled });
    if (!result?.success) {
        showNotification(window.i18n.get('notifications.save_failed') || 'Failed to toggle mapping', 'error');
        return;
    }
    const m = eventMappings.get(eventName);
    if (m) m.enabled = newEnabled;

    // If this is the selected event, sync the header toggle
    if (eventName === selectedEventName) {
        const el = document.getElementById('editor-enabled');
        if (el) el.checked = newEnabled;
    }
}


// ── Deassign ──────────────────────────────────────────────────────────────────

function openDeassignModal() {
    const pairs = getFilteredEvents().filter(({ mapping }) => mapping?.effect != null);

    document.getElementById('deassign-count').textContent = pairs.length;

    const listEl = document.getElementById('deassign-event-list');
    if (listEl) {
        listEl.innerHTML = pairs.slice(0, 50).map(({ event }) =>
            `<div class="text-white/50 font-mono text-xs py-0.5">${escapeHtml(event.name)}</div>`
        ).join('');
        if (pairs.length > 50) {
            listEl.innerHTML += `<div class="text-white/30 text-xs mt-1">...and ${pairs.length - 50} more</div>`;
        }
    }

    const descEl = document.getElementById('deassign-filter-desc');
    if (descEl) {
        const parts = [];
        if (currentCategory !== 'all') parts.push(`Category: ${currentCategory}`);
        if (mappingFilter !== 'all') parts.push(`Filter: ${mappingFilter}`);
        if (searchQuery) parts.push(`Search: "${searchQuery}"`);
        if (minImportance > 0) parts.push(`Min priority: ${minImportance}+`);
        descEl.textContent = parts.length ? parts.join(', ') : (window.i18n.get('events_page.deassign_active_filters') || 'All mapped events');
    }

    document.getElementById('deassign-confirm-modal')?.classList.remove('hidden');
}

function closeDeassignModal() {
    document.getElementById('deassign-confirm-modal')?.classList.add('hidden');
}

async function confirmDeassign() {
    const pairs = getFilteredEvents().filter(({ mapping }) => mapping?.effect != null);
    let count = 0;

    for (const { event } of pairs) {
        const result = await api('save_event_effect', event.name, null);
        if (result?.success) {
            const m = eventMappings.get(event.name);
            if (m) m.effect = null;
            count++;
        }
    }

    // If selected event was deassigned, reset its panel
    if (selectedEventName && !eventMappings.get(selectedEventName)?.effect) {
        currentEventEffect = null;
        savedEventEffect = null;
        showPanel('no-effect-panel');
        showStepActions(false);
        markClean();
    }

    closeDeassignModal();
    renderEventsList();
    showNotification(window.i18n.interpolate('notifications.deassigned_events', {count}) || `Deassigned ${count} events`, 'success');
}


// ── Event listeners ───────────────────────────────────────────────────────────

function setupFilterListeners() {
    // Search (debounced)
    document.getElementById('search-input')?.addEventListener('input',
        debounce(e => { searchQuery = e.target.value.toLowerCase(); renderEventsList(); }, 200)
    );

    // Category filters
    document.querySelectorAll('.category-filter').forEach(btn =>
        btn.addEventListener('click', function () {
            document.querySelectorAll('.category-filter').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.dataset.category;
            renderEventsList();
        })
    );

    // Mapping filter
    document.querySelectorAll('.mapping-filter').forEach(btn =>
        btn.addEventListener('click', function () {
            document.querySelectorAll('.mapping-filter').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            mappingFilter = this.dataset.filter;
            renderEventsList();
        })
    );

    // Importance slider
    document.getElementById('importance-filter')?.addEventListener('input', function () {
        minImportance = parseInt(this.value, 10);
        const label = document.getElementById('importance-filter-label');
        if (label) label.textContent = minImportance === 0 ? (window.i18n.get('status_strings.all_filter') || 'All') : minImportance + '+';
        renderEventsList();
    });
}

function setupEditorListeners() {
    // Priority slider → sync display + markDirty
    document.getElementById('editor-priority')?.addEventListener('input', function () {
        const valEl = document.getElementById('editor-priority-value');
        if (valEl) valEl.textContent = this.value;
        markDirty();
    });

    // Enabled toggle
    document.getElementById('editor-enabled')?.addEventListener('change', () => markDirty());

    // Effect name input
    document.getElementById('editor-effect-name')?.addEventListener('input', () => markDirty());

    // Template search
    document.getElementById('template-search')?.addEventListener('input', function () {
        const q = this.value.toLowerCase();
        const filtered = q
            ? _allTemplates.filter(t =>
                (t._template_name || t.name || '').toLowerCase().includes(q))
            : _allTemplates;
        renderTemplateList(filtered);
    });

    // Template modal close via overlay
    document.getElementById('template-modal-bg')?.addEventListener('click', closeTemplateModal);

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            if (!document.getElementById('template-modal')?.classList.contains('hidden'))
                closeTemplateModal();
        }
    });
}

function setupDeassignListeners() {
    document.getElementById('btn-deassign-filtered')?.addEventListener('click', openDeassignModal);
    document.getElementById('btn-deassign-cancel')?.addEventListener('click', closeDeassignModal);
    document.getElementById('btn-deassign-confirm')?.addEventListener('click', confirmDeassign);
    document.getElementById('deassign-modal-overlay')?.addEventListener('click', closeDeassignModal);

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            if (!document.getElementById('deassign-confirm-modal')?.classList.contains('hidden'))
                closeDeassignModal();
        }
    });
}


// ── Utilities ─────────────────────────────────────────────────────────────────

function deepClone(obj) {
    if (obj === null || obj === undefined) return obj;
    if (typeof obj === 'string') return obj;
    try { return JSON.parse(JSON.stringify(obj)); } catch { return obj; }
}

// debounce, escapeHtml, escapeAttr — provided by common.js
