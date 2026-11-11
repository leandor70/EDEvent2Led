'use strict';

/**
 * quick-effect-creator.js — Shared modal for creating a new effect from any page.
 *
 * Usage:
 *   openQuickEffectCreator({
 *     presetName: 'FSDJump',          // pre-fill effect name (optional)
 *     category:   'event',            // pre-select category (optional)
 *     onSave:     (effectId) => {}    // called after successful save
 *   });
 *
 * Requires: common.js (api, showNotification, hexToRgb, rgbToHex, escapeHtml, escapeAttr)
 *           color-picker.js (openColorPicker)
 */

// ── Type configuration (mirrors EFFECT_TYPE_CONFIG in effects.js, simplified) ──

const QEC_TYPES = {
    'static_transition': {
        label: 'Static Transition', nColors: 1,
        colorLabels: ['Target Color'],
        defaultColors: [[255, 102, 0]],
        dur: 1000, hasLoop: false, hasDir: false
    },
    'breath': {
        label: 'Breath', nColors: 2,
        colorLabels: ['Color 1', 'Color 2'],
        defaultColors: [[10, 10, 30], [0, 150, 255]],
        dur: 2000, hasLoop: true, hasDir: false
    },
    'color_cycle': {
        label: 'Color Cycle', nColors: -1, minColors: 2,
        colorLabels: null,
        defaultColors: [[255, 0, 80], [255, 160, 0], [0, 220, 80], [0, 100, 255]],
        dur: 3000, hasLoop: true, hasDir: true,
        dirOpts: [['right','Right'],['left','Left'],['down','Down'],['top','Top'],
                  ['tl','Top-Left'],['tr','Top-Right'],['bl','Bottom-Left'],['br','Bottom-Right']],
        speed: { label: 'Speed', default: 1.0, min: 0.1, max: 10.0, step: 0.1 },
    },
    'two_color_nuance': {
        label: 'Two Color Nuance', nColors: 2,
        colorLabels: ['Start Color', 'End Color'],
        defaultColors: [[0, 10, 50], [150, 210, 255]],
        dur: 1500, hasLoop: false, hasDir: true,
        dirOpts: [['right','Right'],['left','Left'],['down','Down'],['top','Top'],
                  ['tl','Top-Left'],['tr','Top-Right'],['bl','Bottom-Left'],['br','Bottom-Right']],
    },
    'four_corner_nuance': {
        label: 'Four Corner Nuance', nColors: 4,
        colorLabels: ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right'],
        defaultColors: [[255, 80, 0], [0, 200, 255], [0, 50, 200], [200, 0, 80]],
        dur: 2000, hasLoop: false, hasDir: false,
    },
    'bloom': {
        label: 'Bloom', nColors: 5,
        colorLabels: ['0%', '25%', '50%', '75%', '100%'],
        defaultColors: [[255, 255, 255], [255, 255, 0], [255, 128, 0], [255, 0, 0], [0, 0, 0]],
        dur: 1000, hasLoop: false, hasDir: false,
        expansion: { label: 'Expansion', default: 2.0, min: 1.0, max: 5.0, step: 0.1 },
    },
    'explosion_ring': {
        label: 'Explosion', nColors: 2,
        colorLabels: ['Ring (peak)', 'Trail (burn)'],
        defaultColors: [[255, 255, 255], [255, 40, 0]],
        dur: 1200, hasLoop: false, hasDir: false, hasNumLoops: true,
        expansion: { label: 'Expansion', default: 2.0, min: 1.0, max: 5.0, step: 0.1 },
        decay: { label: 'Trail Decay', default: 0.4, min: 0.1, max: 1.0, step: 0.05 },
    },
    'wave': {
        label: 'Wave', nColors: 2,
        colorLabels: ['Color 1', 'Color 2'],
        defaultColors: [[0, 10, 40], [0, 160, 255]],
        dur: 2000, hasLoop: false, hasDir: true, hasNumLoops: true,
        dirOpts: [['right','Right'],['left','Left'],['down','Down'],['top','Top'],
                  ['tl','Top-Left'],['tr','Top-Right'],['bl','Bottom-Left'],['br','Bottom-Right']],
        speed: { label: 'Width', default: 8, min: 2, max: 30, step: 1 },
    },
    'directional_flash': {
        label: 'Directional Flash', nColors: 2,
        colorLabels: ['Background', 'Impact zone'],
        defaultColors: [[20, 0, 0], [255, 20, 0]],
        dur: 800, hasLoop: false, hasDir: true, hasNumLoops: true,
        dirOpts: [['right','Right (Starboard)'],['left','Left (Port)'],['top','Front'],['down','Rear']]
    },
    'bump': {
        label: 'Bump', nColors: 2,
        colorLabels: ['Edges', 'Center'],
        defaultColors: [[0, 0, 20], [255, 102, 0]],
        dur: 2000, hasLoop: false, hasDir: true, hasNumLoops: true,
        dirOpts: [['right','Right'],['left','Left'],['down','Down'],['top','Top'],
                  ['tl','Top-Left'],['tr','Top-Right'],['bl','Bottom-Left'],['br','Bottom-Right']],
        speed: { label: 'Speed', default: 1.0, min: 0.1, max: 5.0, step: 0.1 },
    },
    'glitch': {
        label: 'Glitch', nColors: 4,
        colorLabels: ['Base Color', 'Glitch 1', 'Glitch 2', 'Glitch 3'],
        defaultColors: [[10, 10, 30], [255, 0, 80], [0, 255, 200], [255, 220, 0]],
        dur: 5000, hasLoop: false, hasDir: false,
    },
    'fire': {
        label: 'Fire', nColors: 2,
        colorLabels: ['Ember', 'Flame Peak'],
        defaultColors: [[200, 30, 0], [255, 220, 0]],
        dur: 6000, hasLoop: false, hasDir: true,
        dirOpts: [['down', 'Bottom → Top'], ['top', 'Top → Bottom']],
    },
    'matrix_rain': {
        label: 'Matrix Rain', nColors: 3,
        colorLabels: ['Background', 'Trail', 'Head'],
        defaultColors: [[0, 0, 0], [0, 100, 30], [0, 255, 70]],
        dur: 8000, hasLoop: false, hasDir: false,
    },
    'ocean_waves': {
        label: 'Ocean Waves', nColors: 3,
        colorLabels: ['Deep Water', 'Surface', 'Wave Crest'],
        defaultColors: [[0, 15, 60], [0, 70, 150], [150, 210, 255]],
        dur: 6000, hasLoop: false, hasDir: false,
    },
    'plasma': {
        label: 'Plasma', nColors: 5,
        colorLabels: ['Palette 1', 'Palette 2', 'Palette 3', 'Palette 4', 'Palette 5'],
        defaultColors: [[220, 0, 100], [255, 120, 0], [255, 230, 0], [0, 200, 80], [0, 100, 255]],
        dur: 6000, hasLoop: false, hasDir: false,
    },
    'aurora': {
        label: 'Aurora', nColors: 3,
        colorLabels: ['Band 1', 'Band 2', 'Band 3'],
        defaultColors: [[0, 220, 80], [0, 160, 200], [80, 0, 220]],
        dur: 8000, hasLoop: false, hasDir: false,
    },
    'parallax_stars': {
        label: 'Parallax Stars', nColors: 4,
        colorLabels: ['Background', 'Far Stars', 'Mid Stars', 'Near Stars'],
        defaultColors: [[0, 0, 5], [60, 80, 180], [150, 175, 240], [255, 255, 255]],
        dur: 8000, hasLoop: false, hasDir: true,
        dirOpts: [['left','Left'],['right','Right']],
        speed: { label: 'Scroll Speed', default: 5.0, min: 0.5, max: 20.0, step: 0.5 },
    },
    'lightning': {
        label: 'Lightning', nColors: 2,
        colorLabels: ['Background', 'Bolt Color'],
        defaultColors: [[3, 3, 20], [200, 220, 255]],
        dur: 10000, hasLoop: false, hasDir: false,
    },
};

// ── Module state ──────────────────────────────────────────────────────────────

let _qec_modal   = null;  // modal DOM element (lazy-created)
let _qec_steps   = [];    // array of step objects
let _qec_opts    = {};    // current openQuickEffectCreator() call options
let _qec_edit_id = null;  // effect ID being edited (null = create mode)

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Open the quick effect creator modal.
 * @param {object} opts
 * @param {string}   [opts.presetName]     Pre-fill the effect name field (create mode)
 * @param {string}   [opts.category]       Pre-select category ('event'|'status'|'general')
 * @param {object}   [opts.existingEffect] Full effect object to edit (activates edit mode)
 * @param {Function} [opts.onSave]         Called with (effectId) after successful save
 */
function openQuickEffectCreator(opts) {
    _qec_opts = opts || {};
    _qec_edit_id = _qec_opts.existingEffect?.id || null;
    _qec_ensure_modal();

    const isEdit = !!_qec_edit_id;
    const effect = _qec_opts.existingEffect;

    // Update header title/subtitle for edit vs create
    const titleEl = document.getElementById('qec-header-title');
    const subtitleEl = document.getElementById('qec-header-subtitle');
    const iconEl = document.getElementById('qec-header-icon');
    if (titleEl) titleEl.textContent = isEdit ? 'Edit Effect' : 'Quick Create Effect';
    if (subtitleEl) subtitleEl.textContent = isEdit
        ? 'Editing existing effect — changes apply immediately to all mappings'
        : 'Marked as NEW for later refinement in the Effects Editor';
    if (iconEl) iconEl.textContent = isEdit ? 'edit' : 'bolt';

    // Pre-fill name
    const nameEl = document.getElementById('qec-name');
    if (nameEl) {
        if (isEdit) nameEl.value = effect.name || '';
        else nameEl.value = _qec_opts.presetName ? `${_qec_opts.presetName} Effect` : '';
    }

    // Pre-select category
    const catEl = document.getElementById('qec-category');
    if (catEl) {
        const cat = isEdit ? (effect.category || 'general') : (_qec_opts.category || '');
        if (cat) catEl.value = cat;
    }

    // Load steps: existing effect steps or one blank step
    if (isEdit && effect.steps?.length) {
        _qec_steps = effect.steps.map(s => ({
            effect_type: s.effect_type,
            params: Object.assign({
                colors: [[255, 102, 0]],
                duration_ms: 1000,
                direction: null,
                loop_infinite: false,
                num_loops: 3
            }, s.params)
        }));
    } else {
        _qec_steps = [_qec_make_step('static_transition')];
    }
    _qec_render_steps();

    // Move to end of <body> on every open so DOM painter order beats any
    // backdrop-filter compositing layer created by parent modals (e.g. status/events).
    document.body.appendChild(_qec_modal);

    _qec_modal.classList.remove('hidden');
    // Focus name input
    setTimeout(() => nameEl && nameEl.focus(), 50);
}

// ── Internal: modal creation ──────────────────────────────────────────────────

function _qec_ensure_modal() {
    if (_qec_modal) return;

    _qec_modal = document.createElement('div');
    _qec_modal.id = 'qec-modal';
    _qec_modal.className = 'hidden fixed inset-0 flex items-start justify-center';
    // z-index 10050: above events modal (10001) and status modal; below color-picker (10100).
    // padding set via style (not cssText which would wipe z-index set above).
    _qec_modal.style.zIndex = '10050';
    _qec_modal.style.paddingTop = '4vh';
    _qec_modal.style.paddingBottom = '4vh';

    _qec_modal.innerHTML = `
        <div class="absolute inset-0 bg-black/75 backdrop-blur-sm" id="qec-backdrop"></div>
        <div class="relative w-[90vw] max-w-[860px] flex flex-col overflow-hidden"
             style="background:rgba(0,0,0,0.55);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
                    border:1px solid rgba(255,102,0,0.35);border-radius:12px;
                    box-shadow:0 20px 60px rgba(0,0,0,0.7),0 0 0 1px rgba(255,102,0,0.15);
                    max-height:92vh;transform:translateZ(0);will-change:transform;">

            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-4 flex-shrink-0"
                 style="border-bottom:1px solid rgba(255,102,0,0.2);">
                <div class="flex items-center gap-3">
                    <span id="qec-header-icon" class="material-symbols-outlined text-2xl" style="color:var(--primary-accent)">bolt</span>
                    <div>
                        <div id="qec-header-title" class="orbitron text-base font-bold tracking-widest text-white uppercase">Quick Create Effect</div>
                        <div id="qec-header-subtitle" class="text-xs text-white/55 mt-0.5">Marked as NEW for later refinement in the Effects Editor</div>
                    </div>
                </div>
                <button id="qec-close"
                        class="transition-all rounded p-2"
                        style="background:rgba(255,102,0,0.1);border:1px solid rgba(255,102,0,0.3);color:var(--primary-accent);"
                        onmouseover="this.style.background='rgba(255,102,0,0.2)'"
                        onmouseout="this.style.background='rgba(255,102,0,0.1)'">
                    <span class="material-symbols-outlined text-xl">close</span>
                </button>
            </div>

            <!-- Body (scrollable) -->
            <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">

                <!-- Name + Category row -->
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs uppercase tracking-widest text-white/60 mb-1.5">Effect Name</label>
                        <input id="qec-name" type="text" placeholder="e.g. Hyperspace Jump Flash"
                               style="width:100%;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.15);
                                      border-radius:6px;padding:8px 12px;color:#fff;font-size:13px;outline:none;
                                      box-sizing:border-box;transition:border-color 0.15s;"
                               onfocus="this.style.borderColor='rgba(255,102,0,0.6)'"
                               onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
                    </div>
                    <div>
                        <label class="block text-xs uppercase tracking-widest text-white/60 mb-1.5">Category</label>
                        <select id="qec-category"
                                style="width:100%;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.15);
                                       border-radius:6px;padding:8px 12px;color:#fff;font-size:13px;outline:none;
                                       box-sizing:border-box;transition:border-color 0.15s;"
                                onfocus="this.style.borderColor='rgba(255,102,0,0.6)'"
                                onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
                            <option value="event">Event</option>
                            <option value="status">Status</option>
                            <option value="Travel">Travel</option>
                            <option value="Combat">Combat</option>
                            <option value="Exploration">Exploration</option>
                            <option value="Trade">Trade</option>
                            <option value="Station Services">Station Services</option>
                            <option value="general">General</option>
                        </select>
                    </div>
                </div>

                <!-- Steps -->
                <div>
                    <div class="text-xs uppercase tracking-widest text-white/60 mb-2">Effect Steps</div>
                    <div id="qec-steps" class="space-y-2"></div>
                    <button id="qec-add-step"
                            class="mt-2 w-full py-2 border border-dashed border-white/20 rounded text-white/40 text-sm
                                   hover:border-[rgba(255,102,0,0.4)] hover:text-[var(--primary-accent)] transition-colors
                                   flex items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-sm">add</span>
                        Add Step
                    </button>
                </div>

            </div>

            <!-- Footer -->
            <div class="flex items-center justify-between px-6 py-4 flex-shrink-0"
                 style="border-top:1px solid rgba(255,102,0,0.2);">
                <p class="text-xs text-white/45 italic flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-sm text-violet-400">info</span>
                    Advanced params can be refined in the Effects Editor
                </p>
                <div class="flex gap-3">
                    <button id="qec-cancel"
                            class="px-5 py-2 text-sm border border-white/15 text-white/60 rounded
                                   hover:bg-white/5 transition-colors uppercase tracking-wider">
                        Cancel
                    </button>
                    <button id="qec-save"
                            class="px-7 py-2 text-sm orbitron font-bold tracking-wider rounded transition-all
                                   hover:brightness-110 shadow-lg uppercase flex items-center gap-2"
                            style="background:rgba(255,102,0,0.9);color:#000;box-shadow:0 0 15px rgba(255,102,0,0.3);">
                        <span class="material-symbols-outlined text-sm">check_circle</span>
                        Save &amp; Use
                    </button>
                </div>
            </div>
        </div>`;

    document.body.appendChild(_qec_modal);

    // Wire events
    document.getElementById('qec-close').addEventListener('click', _qec_close);
    document.getElementById('qec-cancel').addEventListener('click', _qec_close);
    document.getElementById('qec-backdrop').addEventListener('click', _qec_close);
    document.getElementById('qec-add-step').addEventListener('click', _qec_add_step);
    document.getElementById('qec-save').addEventListener('click', _qec_save);
}

function _qec_close() {
    if (_qec_modal) _qec_modal.classList.add('hidden');
    _qec_steps = [];
}

// ── Internal: step management ─────────────────────────────────────────────────

function _qec_make_step(effectType) {
    const cfg = QEC_TYPES[effectType] || QEC_TYPES['static_transition'];
    const numColors = cfg.nColors === -1 ? cfg.minColors : cfg.nColors;
    const colors = (cfg.defaultColors || []).slice(0, numColors);
    // Pad with a fallback color if defaults don't cover all slots
    while (colors.length < numColors) colors.push([128, 128, 128]);

    const params = {
        colors: colors.map(c => [...c]),
        duration_ms: cfg.dur
    };
    if (cfg.hasDir)      params.direction        = (cfg.dirOpts ? cfg.dirOpts[0][0] : 'right');
    if (cfg.hasLoop)     { params.loop_infinite = false; params.num_loops = 3; }
    if (cfg.hasNumLoops) params.num_loops        = params.num_loops ?? 1;
    if (cfg.speed)       params.speed            = cfg.speed.default;
    if (cfg.expansion)   params.expansion_factor = cfg.expansion.default;
    if (cfg.decay)       params.decay_rate       = cfg.decay.default;

    return { effect_type: effectType, params };
}

function _qec_add_step() {
    _qec_steps.push(_qec_make_step('static_transition'));
    _qec_render_steps();
}

function _qec_delete_step(idx) {
    _qec_steps.splice(idx, 1);
    _qec_render_steps();
}

function _qec_change_type(idx, newType) {
    _qec_steps[idx] = _qec_make_step(newType);
    _qec_render_steps();
}

// ── Internal: rendering ───────────────────────────────────────────────────────

function _qec_render_steps() {
    const container = document.getElementById('qec-steps');
    if (!container) return;

    if (_qec_steps.length === 0) {
        container.innerHTML = '<p class="text-sm text-white/30 italic py-2">No steps yet.</p>';
        return;
    }

    container.innerHTML = _qec_steps.map((step, idx) => _qec_step_html(step, idx)).join('');

    // Wire direction selects
    container.querySelectorAll('.qec-dir-select').forEach(sel => {
        sel.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.direction = e.target.value;
        });
    });

    // Wire duration inputs
    container.querySelectorAll('.qec-dur-input').forEach(inp => {
        inp.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.duration_ms = Math.max(100, parseInt(e.target.value) || 1000);
        });
    });

    // Wire loop toggles
    container.querySelectorAll('.qec-loop-toggle').forEach(cb => {
        cb.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.loop_infinite = e.target.checked;
            // Re-render this step to show/hide num_loops
            _qec_rerender_step(idx);
        });
    });

    // Wire num_loops inputs
    container.querySelectorAll('.qec-loops-input').forEach(inp => {
        inp.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.num_loops = Math.max(0, parseInt(e.target.value) || 1);
        });
    });

    // Wire speed inputs
    container.querySelectorAll('.qec-speed-input').forEach(inp => {
        inp.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.speed = parseFloat(e.target.value) || 1.0;
        });
    });

    // Wire expansion_factor inputs
    container.querySelectorAll('.qec-expansion-input').forEach(inp => {
        inp.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.expansion_factor = parseFloat(e.target.value) || 2.0;
        });
    });

    // Wire decay_rate inputs
    container.querySelectorAll('.qec-decay-input').forEach(inp => {
        inp.addEventListener('change', e => {
            const idx = +e.target.dataset.idx;
            _qec_steps[idx].params.decay_rate = parseFloat(e.target.value) || 0.4;
        });
    });

    // Wire type selects
    container.querySelectorAll('.qec-type-select').forEach(sel => {
        sel.addEventListener('change', e => {
            _qec_change_type(+e.target.dataset.idx, e.target.value);
        });
    });

    // Wire color-cycle add/remove color buttons
    container.querySelectorAll('.qec-add-color').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = +btn.dataset.idx;
            const cfg = QEC_TYPES[_qec_steps[idx].effect_type];
            const max = (cfg && cfg.maxColors) || 10;
            if (_qec_steps[idx].params.colors.length < max) {
                _qec_steps[idx].params.colors.push([128, 128, 128]);
                _qec_rerender_step(idx);
            }
        });
    });
    container.querySelectorAll('.qec-remove-color').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = +btn.dataset.idx;
            const cfg = QEC_TYPES[_qec_steps[idx].effect_type];
            const min = (cfg && cfg.minColors) || 2;
            if (_qec_steps[idx].params.colors.length > min) {
                _qec_steps[idx].params.colors.pop();
                _qec_rerender_step(idx);
            }
        });
    });
}

function _qec_rerender_step(idx) {
    const container = document.getElementById('qec-steps');
    const stepEl = container?.querySelector(`[data-step="${idx}"]`);
    if (!stepEl) return;
    const newHtml = document.createElement('div');
    newHtml.innerHTML = _qec_step_html(_qec_steps[idx], idx);
    const newStep = newHtml.firstElementChild;
    stepEl.replaceWith(newStep);

    // Re-wire events for this step only
    newStep.querySelector('.qec-dir-select')?.addEventListener('change', e => {
        _qec_steps[idx].params.direction = e.target.value;
    });
    newStep.querySelector('.qec-dur-input')?.addEventListener('change', e => {
        _qec_steps[idx].params.duration_ms = Math.max(100, parseInt(e.target.value) || 1000);
    });
    newStep.querySelector('.qec-loop-toggle')?.addEventListener('change', e => {
        _qec_steps[idx].params.loop_infinite = e.target.checked;
        _qec_rerender_step(idx);
    });
    newStep.querySelector('.qec-loops-input')?.addEventListener('change', e => {
        _qec_steps[idx].params.num_loops = Math.max(0, parseInt(e.target.value) || 1);
    });
    newStep.querySelector('.qec-speed-input')?.addEventListener('change', e => {
        _qec_steps[idx].params.speed = parseFloat(e.target.value) || 1.0;
    });
    newStep.querySelector('.qec-expansion-input')?.addEventListener('change', e => {
        _qec_steps[idx].params.expansion_factor = parseFloat(e.target.value) || 2.0;
    });
    newStep.querySelector('.qec-decay-input')?.addEventListener('change', e => {
        _qec_steps[idx].params.decay_rate = parseFloat(e.target.value) || 0.4;
    });
    newStep.querySelector('.qec-type-select')?.addEventListener('change', e => {
        _qec_change_type(idx, e.target.value);
    });
    newStep.querySelector('.qec-add-color')?.addEventListener('click', () => {
        const cfg = QEC_TYPES[_qec_steps[idx].effect_type];
        if (_qec_steps[idx].params.colors.length < ((cfg && cfg.maxColors) || 10)) {
            _qec_steps[idx].params.colors.push([128, 128, 128]);
            _qec_rerender_step(idx);
        }
    });
    newStep.querySelector('.qec-remove-color')?.addEventListener('click', () => {
        const cfg = QEC_TYPES[_qec_steps[idx].effect_type];
        const min = (cfg && cfg.minColors) || 2;
        if (_qec_steps[idx].params.colors.length > min) {
            _qec_steps[idx].params.colors.pop();
            _qec_rerender_step(idx);
        }
    });
}

function _qec_step_html(step, idx) {
    const cfg = QEC_TYPES[step.effect_type] || QEC_TYPES['static_transition'];
    const isVariable = cfg.nColors === -1;

    // Type dropdown
    const typeOptions = Object.entries(QEC_TYPES).map(([val, c]) =>
        `<option value="${val}"${val === step.effect_type ? ' selected' : ''}>${c.label}</option>`
    ).join('');

    // Color pickers
    const colorLabels = cfg.colorLabels || step.params.colors.map((_, i) => `Color ${i + 1}`);
    const colorSwatches = step.params.colors.map((rgb, ci) => {
        const hex = '#' + rgb.map(v => v.toString(16).padStart(2, '0')).join('');
        const label = colorLabels[ci] || `Color ${ci + 1}`;
        return `
            <div class="flex flex-col items-center gap-1">
                <button class="qec-color-swatch"
                        data-idx="${idx}" data-ci="${ci}"
                        style="background:${hex};width:28px;height:28px;border-radius:5px;
                               border:2px solid rgba(255,255,255,0.2);cursor:pointer;
                               transition:border-color 0.15s;flex-shrink:0;"
                        onmouseover="this.style.borderColor='rgba(255,102,0,0.7)'"
                        onmouseout="this.style.borderColor='rgba(255,255,255,0.2)'"
                        title="${label}"></button>
                <span style="font-size:9px;color:rgba(255,255,255,0.35);text-align:center;max-width:28px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${label}</span>
            </div>`;
    }).join('');

    // Variable color controls (color_cycle)
    const varColorBtns = isVariable ? `
        <div class="flex gap-1 ml-1 self-end pb-1">
            <button class="qec-add-color px-1.5 py-0.5 text-xs border border-white/20 rounded
                           hover:border-[rgba(255,102,0,0.4)] text-white/50 hover:text-[var(--primary-accent)] transition-colors"
                    data-idx="${idx}" title="Add color">+</button>
            <button class="qec-remove-color px-1.5 py-0.5 text-xs border border-white/20 rounded
                           hover:border-red-400/40 text-white/50 hover:text-red-400 transition-colors"
                    data-idx="${idx}" title="Remove color">−</button>
        </div>` : '';

    // Direction select
    const dirOpts = cfg.hasDir ? (cfg.dirOpts || [
        ['right','Right'],['left','Left'],['down','Down'],['top','Top'],
        ['tl','Top-Left'],['tr','Top-Right'],['bl','Bottom-Left'],['br','Bottom-Right']
    ]) : null;
    const dirSelect = dirOpts ? `
        <div class="flex items-center gap-1.5">
            <span class="text-xs text-white/55 uppercase tracking-wider whitespace-nowrap">Dir</span>
            <select class="qec-dir-select"
                    data-idx="${idx}"
                    style="background:rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.8);
                           font-size:11px;border-radius:5px;padding:3px 6px;outline:none;"
                    onfocus="this.style.borderColor='rgba(255,102,0,0.5)'"
                    onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
                ${dirOpts.map(([v, l]) => `<option value="${v}"${v === (step.params.direction || dirOpts[0][0]) ? ' selected' : ''}>${l}</option>`).join('')}
            </select>
        </div>` : '';

    // Loop controls
    const loopControls = cfg.hasLoop ? `
        <div class="flex items-center gap-2 ml-1">
            <label class="flex items-center gap-1.5 cursor-pointer">
                <div class="relative w-8 h-4 flex-shrink-0">
                    <input type="checkbox" class="qec-loop-toggle sr-only" data-idx="${idx}"
                           ${step.params.loop_infinite ? 'checked' : ''}>
                    <div class="w-8 h-4 rounded-full transition-colors ${step.params.loop_infinite ? 'bg-[var(--primary-accent)]' : 'bg-white/15'}"></div>
                    <div class="absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white transition-transform ${step.params.loop_infinite ? 'translate-x-4' : ''}"></div>
                </div>
                <span class="text-xs text-white/65 uppercase tracking-wider whitespace-nowrap">Loop ∞</span>
            </label>
            ${!step.params.loop_infinite ? `
            <div class="flex items-center gap-1">
                <span class="text-xs text-white/55">×</span>
                <input type="number" class="qec-loops-input"
                       data-idx="${idx}" value="${step.params.num_loops || 3}" min="1" max="50"
                       style="width:44px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.15);
                              color:rgba(255,255,255,0.8);font-size:11px;border-radius:5px;
                              padding:2px 6px;outline:none;"
                       onfocus="this.style.borderColor='rgba(255,102,0,0.5)'"
                       onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
            </div>` : ''}
        </div>` : '';

    // ── Extra parameters (Row 3) ────────────────────────────────────────────────
    const INPUT_STYLE = `background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.15);
                         color:rgba(255,255,255,0.8);font-size:11px;border-radius:5px;
                         padding:2px 6px;outline:none;`;
    const FOCUS_IN  = `this.style.borderColor='rgba(255,102,0,0.5)'`;
    const FOCUS_OUT = `this.style.borderColor='rgba(255,255,255,0.15)'`;
    const LABEL_STYLE = `font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;
                         letter-spacing:0.05em;white-space:nowrap;`;

    // Speed
    const speedCtrl = cfg.speed ? `
        <div style="display:flex;align-items:center;gap:4px;">
            <span style="${LABEL_STYLE}">${cfg.speed.label}</span>
            <input type="number" class="qec-speed-input" data-idx="${idx}"
                   value="${step.params.speed ?? cfg.speed.default}"
                   min="${cfg.speed.min}" max="${cfg.speed.max}" step="${cfg.speed.step}"
                   style="width:52px;${INPUT_STYLE}"
                   onfocus="${FOCUS_IN}" onblur="${FOCUS_OUT}">
        </div>` : '';

    // Expansion factor
    const expansionCtrl = cfg.expansion ? `
        <div style="display:flex;align-items:center;gap:4px;">
            <span style="${LABEL_STYLE}">${cfg.expansion.label}</span>
            <input type="number" class="qec-expansion-input" data-idx="${idx}"
                   value="${step.params.expansion_factor ?? cfg.expansion.default}"
                   min="${cfg.expansion.min}" max="${cfg.expansion.max}" step="${cfg.expansion.step}"
                   style="width:52px;${INPUT_STYLE}"
                   onfocus="${FOCUS_IN}" onblur="${FOCUS_OUT}">
        </div>` : '';

    // Decay rate
    const decayCtrl = cfg.decay ? `
        <div style="display:flex;align-items:center;gap:4px;">
            <span style="${LABEL_STYLE}">${cfg.decay.label}</span>
            <input type="number" class="qec-decay-input" data-idx="${idx}"
                   value="${step.params.decay_rate ?? cfg.decay.default}"
                   min="${cfg.decay.min}" max="${cfg.decay.max}" step="${cfg.decay.step}"
                   style="width:52px;${INPUT_STYLE}"
                   onfocus="${FOCUS_IN}" onblur="${FOCUS_OUT}">
        </div>` : '';

    // Standalone num_loops (for effects without loop_infinite toggle)
    const numLoopsCtrl = (cfg.hasNumLoops && !cfg.hasLoop) ? `
        <div style="display:flex;align-items:center;gap:4px;">
            <span style="${LABEL_STYLE}">Reps</span>
            <input type="number" class="qec-loops-input" data-idx="${idx}"
                   value="${step.params.num_loops ?? 1}" min="0" max="100"
                   style="width:44px;${INPUT_STYLE}"
                   onfocus="${FOCUS_IN}" onblur="${FOCUS_OUT}"
                   title="Repetitions (0 = infinite)">
            <span style="font-size:9px;color:rgba(255,255,255,0.25);">0=∞</span>
        </div>` : '';

    const extraRow = (speedCtrl || expansionCtrl || decayCtrl || numLoopsCtrl)
        ? `<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-left:28px;
                       border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
               ${speedCtrl}${expansionCtrl}${decayCtrl}${numLoopsCtrl}
           </div>`
        : '';

    return `
        <div class="qec-step-card"
             style="display:flex;flex-direction:column;gap:8px;padding:12px;border-radius:6px;
                    border:1px solid rgba(255,255,255,0.1);background:rgba(0,0,0,0.4);"
             data-step="${idx}">

            <!-- Row 1: index + type + duration + delete -->
            <div class="flex items-center gap-2">
                <span class="w-5 h-5 rounded-full bg-[rgba(255,102,0,0.2)] text-[var(--primary-accent)]
                             text-xs font-bold flex items-center justify-center flex-shrink-0">${idx + 1}</span>

                <select class="qec-type-select"
                        data-idx="${idx}"
                        style="flex:1;background:rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.15);
                               color:rgba(255,255,255,0.9);font-size:13px;border-radius:5px;
                               padding:4px 8px;outline:none;"
                        onfocus="this.style.borderColor='rgba(255,102,0,0.5)'"
                        onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
                    ${typeOptions}
                </select>

                <div class="flex items-center gap-1 flex-shrink-0">
                    <input type="number" class="qec-dur-input"
                           data-idx="${idx}" value="${step.params.duration_ms}" min="100" max="60000"
                           style="width:72px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.15);
                                  color:rgba(255,255,255,0.8);font-size:11px;border-radius:5px;
                                  padding:4px 8px;outline:none;"
                           onfocus="this.style.borderColor='rgba(255,102,0,0.5)'"
                           onblur="this.style.borderColor='rgba(255,255,255,0.15)'">
                    <span class="text-xs text-white/50">ms</span>
                </div>

                <button class="qec-del-step flex-shrink-0 p-1 text-white/30 hover:text-red-400
                               hover:bg-red-400/10 rounded transition-colors"
                        onclick="_qec_delete_step(${idx})" title="Delete step">
                    <span class="material-symbols-outlined text-sm">delete</span>
                </button>
            </div>

            <!-- Row 2: colors + direction + loop -->
            <div class="flex items-end gap-2 flex-wrap pl-7">
                ${colorSwatches}
                ${varColorBtns}
                ${dirSelect ? `<div class="ml-2">${dirSelect.trim()}</div>` : ''}
                ${loopControls ? `<div class="ml-1">${loopControls.trim()}</div>` : ''}
            </div>

            <!-- Row 3: extra params (speed, expansion, decay, reps, normalized) -->
            ${extraRow}
        </div>`;
}

// ── Internal: color picking ───────────────────────────────────────────────────

// Delegated listener for color swatches — attached once after modal creation
document.addEventListener('click', function(e) {
    const swatch = e.target.closest('.qec-color-swatch');
    if (!swatch || !document.getElementById('qec-modal')?.contains(swatch)) return;
    if (typeof openColorPicker !== 'function') {
        showNotification('Color picker not available', 'error');
        return;
    }
    const idx = +swatch.dataset.idx;
    const ci  = +swatch.dataset.ci;
    const currentRgb = _qec_steps[idx]?.params.colors[ci] || [128, 128, 128];
    const currentHex = '#' + currentRgb.map(v => v.toString(16).padStart(2, '0')).join('');

    openColorPicker(currentHex, (newHex) => {
        // hexToRgb may return [r,g,b] array (common.js) or {r,g,b} object (events.js override)
        const raw = hexToRgb(newHex);
        if (!raw) return;
        const r = Array.isArray(raw) ? raw[0] : raw.r;
        const g = Array.isArray(raw) ? raw[1] : raw.g;
        const b = Array.isArray(raw) ? raw[2] : raw.b;
        _qec_steps[idx].params.colors[ci] = [r, g, b];
        swatch.style.background = newHex;
    });
});

// ── Internal: save ────────────────────────────────────────────────────────────

async function _qec_save() {
    const name = (document.getElementById('qec-name')?.value || '').trim();
    const category = document.getElementById('qec-category')?.value || 'event';

    if (!name) {
        showNotification('Please enter an effect name', 'error');
        document.getElementById('qec-name')?.focus();
        return;
    }
    if (_qec_steps.length === 0) {
        showNotification('Please add at least one step', 'error');
        return;
    }

    const steps = _qec_steps.map((step, idx) => ({
        step_id: `step_${idx}`,
        effect_type: step.effect_type,
        params: step.params
    }));

    const payload = {
        name,
        description: 'Quick-created — refine in Effects Editor',
        category,
        steps,
        topology_support: ['0D', '1D', '2D'],
        post_behavior: 'static_color',
        is_quick_created: true,
        created_timestamp: Date.now() / 1000
    };

    const btn = document.getElementById('qec-save');
    if (btn) btn.disabled = true;

    try {
        let result, savedId;
        if (_qec_edit_id) {
            // Edit mode: update existing effect (preserves ID and all mappings)
            result = await api('update_effect', _qec_edit_id, payload);
            savedId = _qec_edit_id;
            if (!result?.success) {
                showNotification(`Failed to update effect: ${result?.error || 'Unknown error'}`, 'error');
                return;
            }
            showNotification(`"${name}" updated!`, 'success');
        } else {
            // Create mode
            result = await api('create_effect', payload);
            savedId = result?.id;
            if (!result?.success) {
                showNotification(`Failed to create effect: ${result?.error || 'Unknown error'}`, 'error');
                return;
            }
            showNotification(`"${name}" created!`, 'success');
        }
        _qec_close();
        if (typeof _qec_opts.onSave === 'function') {
            _qec_opts.onSave(savedId);
        }
    } catch (err) {
        showNotification(`Error: ${err}`, 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Expose globally
window.openQuickEffectCreator = openQuickEffectCreator;
