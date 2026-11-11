/**
 * effect-editor-module.js
 * Reusable step-editor UI for VisualEffect objects.
 *
 * Encapsulates EFFECT_TYPE_CONFIG, step-card rendering, drag-and-drop,
 * and color-timeline update into a self-contained class.
 *
 * Used by:
 *   - effects.js  (Templates Library page)
 *   - events.js   (split-pane event editor)
 *   - status.js   (ON/OFF modal)
 *
 * Depends on globals from common.js:
 *   hexToRgb(), rgbToHex(), throttle(), openColorPicker(), showNotification()
 */

// ── EFFECT_TYPE_CONFIG ──────────────────────────────────────────────────────

const EFFECT_TYPE_CONFIG = {
    'static_transition': {
        label: 'Static Transition',
        colors: 1,
        colorLabels: ['Target Color'],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 1000, min: 100, max: 10000 }
        },
        canFadeIn: false,
        topology: ['0D', '1D', '2D']
    },
    'breath': {
        label: 'Breath',
        colors: 2,
        colorLabels: ['Color 1', 'Color 2'],
        defaultColors: [[10, 10, 30], [0, 150, 255]],
        params: {
            duration: { type: 'number', label: 'Cycle Duration (ms)', default: 2000, min: 100, max: 10000 },
            num_loops: { type: 'number', label: 'Repetitions', default: 1, min: 1, max: 50 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['0D', '1D', '2D']
    },
    'color_cycle': {
        label: 'Color Cycle',
        colors: 'variable',
        colorLabels: null,
        minColors: 2,
        maxColors: 10,
        defaultColors: [[255, 0, 80], [255, 160, 0], [0, 220, 80], [0, 100, 255]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 3000, min: 100, max: 10000 },
            direction: {
                type: 'select', label: 'Direction', default: 'right',
                options: [
                    { value: 'top', label: 'Top' }, { value: 'down', label: 'Down' },
                    { value: 'left', label: 'Left' }, { value: 'right', label: 'Right' },
                    { value: 'tl', label: 'Top-Left' }, { value: 'tr', label: 'Top-Right' },
                    { value: 'bl', label: 'Bottom-Left' }, { value: 'br', label: 'Bottom-Right' }
                ]
            },
            speed: { type: 'number', label: 'Speed', default: 1.0, min: 0.1, max: 10.0, step: 0.1 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['1D', '2D'],
        supportsNormalized: true
    },
    'two_color_nuance': {
        label: 'Two Color Nuance',
        colors: 2,
        colorLabels: ['Start Color', 'End Color'],
        defaultColors: [[0, 10, 50], [150, 210, 255]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 1500, min: 100, max: 10000 },
            direction: {
                type: 'select', label: 'Direction', default: 'right',
                options: [
                    { value: 'top', label: 'Top' }, { value: 'down', label: 'Down' },
                    { value: 'left', label: 'Left' }, { value: 'right', label: 'Right' },
                    { value: 'tl', label: 'Top-Left' }, { value: 'tr', label: 'Top-Right' },
                    { value: 'bl', label: 'Bottom-Left' }, { value: 'br', label: 'Bottom-Right' }
                ]
            },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['1D', '2D'],
        supportsNormalized: true
    },
    'four_corner_nuance': {
        label: 'Four Corner Nuance',
        colors: 4,
        colorLabels: ['Top-Left', 'Top-Right', 'Bottom-Left', 'Bottom-Right'],
        defaultColors: [[255, 80, 0], [0, 200, 255], [0, 50, 200], [200, 0, 80]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 2000, min: 100, max: 10000 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D']
    },
    'bloom': {
        label: 'Bloom',
        colors: 5,
        colorLabels: ['t=0%', 't=25%', 't=50%', 't=75%', 't=100%'],
        defaultColors: [[255, 255, 255], [255, 255, 0], [255, 128, 0], [255, 0, 0], [0, 0, 0]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 1000, min: 100, max: 10000 },
            expansion_factor: { type: 'number', label: 'Expansion Factor', default: 2.0, min: 1.0, max: 5.0, step: 0.1 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['1D', '2D'],
        supportsNormalized: true
    },
    'explosion_ring': {
        label: 'Explosion',
        colors: 2,
        colorLabels: ['Ring (peak)', 'Trail (burn)'],
        defaultColors: [[255, 255, 255], [255, 40, 0]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 1200, min: 200, max: 10000 },
            expansion_factor: { type: 'number', label: 'Expansion Factor', default: 2.0, min: 1.0, max: 5.0, step: 0.1 },
            ring_width: { type: 'number', label: 'Ring Width', default: 0.1, min: 0.05, max: 0.5, step: 0.05 },
            decay_rate: { type: 'number', label: 'Trail Decay', default: 0.4, min: 0.1, max: 1.0, step: 0.05 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'wave': {
        label: 'Wave',
        colors: 2,
        colorLabels: ['Color 1', 'Color 2'],
        defaultColors: [[0, 10, 40], [0, 160, 255]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 2000, min: 100, max: 10000 },
            direction: {
                type: 'select', label: 'Direction', default: 'right',
                options: [
                    { value: 'top', label: 'Top' }, { value: 'down', label: 'Down' },
                    { value: 'left', label: 'Left' }, { value: 'right', label: 'Right' },
                    { value: 'tl', label: 'Top-Left' }, { value: 'tr', label: 'Top-Right' },
                    { value: 'bl', label: 'Bottom-Left' }, { value: 'br', label: 'Bottom-Right' }
                ]
            },
            speed: { type: 'number', label: 'Larghezza onda', default: 8, min: 2, max: 30, step: 1, suffix: '' },
            num_loops: { type: 'number', label: 'Number of Loops', default: 1, min: 0, max: 100 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'directional_flash': {
        label: 'Directional Flash',
        colors: 2,
        colorLabels: ['Background (3/4)', 'Impact zone (1/4)'],
        defaultColors: [[20, 0, 0], [255, 20, 0]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 800, min: 100, max: 5000 },
            direction: {
                type: 'select', label: 'Hit side', default: 'right',
                options: [
                    { value: 'right', label: 'Right (Starboard)' }, { value: 'left', label: 'Left (Port)' },
                    { value: 'top', label: 'Front' }, { value: 'down', label: 'Rear' }
                ]
            },
            num_loops: { type: 'number', label: 'Flashes', default: 1, min: 1, max: 20 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'bump': {
        label: 'Bump',
        colors: 2,
        colorLabels: ['Bordi', 'Centro'],
        defaultColors: [[0, 0, 20], [255, 102, 0]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 2000, min: 100, max: 10000 },
            direction: {
                type: 'select', label: 'Direction', default: 'right',
                options: [
                    { value: 'top', label: 'Top' }, { value: 'down', label: 'Down' },
                    { value: 'left', label: 'Left' }, { value: 'right', label: 'Right' },
                    { value: 'tl', label: 'Top-Left' }, { value: 'tr', label: 'Top-Right' },
                    { value: 'bl', label: 'Bottom-Left' }, { value: 'br', label: 'Bottom-Right' }
                ]
            },
            num_loops: { type: 'number', label: 'Number of Loops', default: 1, min: 0, max: 100 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'glitch': {
        label: 'Glitch',
        colors: 4,
        colorLabels: ['Base Color', 'Glitch Color 1', 'Glitch Color 2', 'Glitch Color 3'],
        defaultColors: [[10, 10, 30], [255, 0, 80], [0, 255, 200], [255, 220, 0]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 5000, min: 500, max: 20000 },
            glitch_percentage: { type: 'number', label: 'Glitch Density', default: 0.15, min: 0.01, max: 0.5, step: 0.01 },
            glitch_duration_ms: { type: 'number', label: 'Glitch Duration (ms)', default: 150, min: 10, max: 500 },
            duration_variability: { type: 'number', label: 'Duration Variation', default: 0.5, min: 0.0, max: 1.0, step: 0.05 },
            persistence_percentage: { type: 'number', label: 'Persistence', default: 0.3, min: 0.0, max: 0.5, step: 0.05 },
            color_variation: { type: 'number', label: 'Color Variation', default: 0.2, min: 0.0, max: 1.0, step: 0.05 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['1D', '2D'],
        supportsNormalized: true
    },
    'fire': {
        label: 'Fire',
        colors: 2,
        colorLabels: ['Ember Color', 'Flame Peak'],
        defaultColors: [[200, 30, 0], [255, 220, 0]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 6000, min: 1000, max: 30000 },
            intensity: { type: 'number', label: 'Intensity (0-1)', default: 0.8, min: 0.1, max: 1.0, step: 0.05 },
            direction: {
                type: 'select', label: 'Direction', default: 'down',
                options: [
                    { value: 'down', label: 'Bottom \u2192 Top' },
                    { value: 'top', label: 'Top \u2192 Bottom' }
                ]
            },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['1D', '2D'],
        supportsNormalized: true
    },
    'matrix_rain': {
        label: 'Matrix Rain',
        colors: 3,
        colorLabels: ['Background', 'Trail Color', 'Head Color'],
        defaultColors: [[0, 0, 0], [0, 100, 30], [0, 255, 70]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 8000, min: 1000, max: 30000 },
            density: { type: 'number', label: 'Column Density', default: 1.0, min: 0.2, max: 3.0, step: 0.1 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'ocean_waves': {
        label: 'Ocean Waves',
        colors: 3,
        colorLabels: ['Deep Water', 'Surface', 'Wave Crest'],
        defaultColors: [[0, 15, 60], [0, 70, 150], [150, 210, 255]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 6000, min: 1000, max: 30000 },
            speed: { type: 'number', label: 'Wave Speed', default: 1.0, min: 0.1, max: 5.0, step: 0.1 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'plasma': {
        label: 'Plasma',
        colors: 5,
        colorLabels: ['Palette 1', 'Palette 2', 'Palette 3', 'Palette 4', 'Palette 5'],
        defaultColors: [[220, 0, 100], [255, 120, 0], [255, 230, 0], [0, 200, 80], [0, 100, 255]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 6000, min: 1000, max: 30000 },
            speed: { type: 'number', label: 'Speed', default: 1.0, min: 0.1, max: 5.0, step: 0.1 },
            wave_weight_h: { type: 'number', label: 'Wave: Horizontal', default: 1.0, min: 0.0, max: 3.0, step: 0.1 },
            wave_weight_v: { type: 'number', label: 'Wave: Vertical', default: 1.0, min: 0.0, max: 3.0, step: 0.1 },
            wave_weight_c: { type: 'number', label: 'Wave: Circular', default: 1.0, min: 0.0, max: 3.0, step: 0.1 },
            wave_weight_d: { type: 'number', label: 'Wave: Diagonal', default: 1.0, min: 0.0, max: 3.0, step: 0.1 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'aurora': {
        label: 'Aurora',
        colors: 3,
        colorLabels: ['Band Color 1', 'Band Color 2', 'Band Color 3'],
        defaultColors: [[0, 220, 80], [0, 160, 200], [80, 0, 220]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 8000, min: 1000, max: 30000 },
            speed: { type: 'number', label: 'Speed', default: 0.5, min: 0.1, max: 3.0, step: 0.1 },
            height: { type: 'number', label: 'Band Height (0-1)', default: 0.4, min: 0.1, max: 0.9, step: 0.05 },
            tail_length: { type: 'number', label: 'Curtain Length (0-1.5)', default: 0.7, min: 0.1, max: 1.5, step: 0.05 },
            wave_frequency: { type: 'number', label: 'Undulation Frequency', default: 0.8, min: 0.1, max: 3.0, step: 0.1 },
            ripple: { type: 'number', label: 'Ripple Intensity (0-1)', default: 0.3, min: 0.0, max: 1.0, step: 0.05 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'parallax_stars': {
        label: 'Parallax Stars',
        colors: 4,
        colorLabels: ['Background', 'Far Stars', 'Mid Stars', 'Near Stars'],
        defaultColors: [[0, 0, 5], [60, 80, 180], [150, 175, 240], [255, 255, 255]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 8000, min: 1000, max: 30000 },
            direction: {
                type: 'select', label: 'Scroll Direction', default: 'left',
                options: [{ value: 'left', label: 'Left' }, { value: 'right', label: 'Right' }]
            },
            speed: { type: 'number', label: 'Scroll Speed (px/s)', default: 5.0, min: 0.5, max: 20.0, step: 0.5 },
            density: { type: 'number', label: 'Star Density', default: 1.0, min: 0.2, max: 5.0, step: 0.1 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['1D', '2D'],
        directionOptions: ['left', 'right'],
        supportsNormalized: true
    },
    'lightning': {
        label: 'Lightning',
        colors: 4,
        colorLabels: ['Background', 'Bolt Color', 'Flash Color', 'Flicker Color'],
        defaultColors: [[3, 3, 20], [200, 220, 255], [255, 255, 255], [20, 20, 60]],
        params: {
            duration: { type: 'number', label: 'Duration (ms)', default: 10000, min: 2000, max: 60000 },
            bolt_interval_ms: { type: 'number', label: 'Strike Interval (ms)', default: 2000, min: 500, max: 10000 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        supportsNormalized: true
    },
    'keyboard_default': {
        label: 'Keyboard Mapping',
        colors: 0,
        colorLabels: [],
        defaultColors: [],
        params: {
            duration: { type: 'number', label: 'Transition (ms)', default: 800, min: 100, max: 5000 },
            fade_in_ms: { type: 'fade_preset', default: 0 }
        },
        canFadeIn: true,
        topology: ['2D'],
        hasKeyboardPreset: true
    }
};


// ── EffectEditorModule ──────────────────────────────────────────────────────

class EffectEditorModule {
    /**
     * @param {Object} opts
     * @param {string}   opts.stepsContainerId   - ID of the container div for step cards
     * @param {string}   [opts.timelineCanvasId] - ID of canvas for color timeline (optional)
     * @param {Function} [opts.onStepsChange]    - Called with current steps array on every change
     */
    constructor({ stepsContainerId, timelineCanvasId = null, onStepsChange = null }) {
        this._stepsContainerId = stepsContainerId;
        this._timelineCanvasId = timelineCanvasId;
        this._onStepsChange    = onStepsChange;

        this._effect           = null;   // current effect data (deep copy, in-memory)
        this._effectTypes      = [];     // [{ value, label }] from API
        this._timelineTimer    = null;
        this._dragAbortCtrl    = null;
    }

    // ── Public API ───────────────────────────────────────────────────────────

    /** Load effect types from API. Must be called before first use. */
    async init() {
        const result = await api('get_effect_types');
        if (result && result.success) {
            this._effectTypes = result.types;
        }
    }

    /** Populate the editor with an effect dict (deep-copied). Pass null to clear. */
    loadEffect(effectData) {
        this._effect = effectData ? JSON.parse(JSON.stringify(effectData)) : null;
        this._render();
    }

    /** Return current steps array read from DOM state. */
    getSteps() {
        return this._collectSteps();
    }

    /** Add a new step with defaults for the given type. */
    addStep(effectType = 'static_transition') {
        if (!this._effect) return;
        const config = EFFECT_TYPE_CONFIG[effectType];
        if (!config) return;

        const numColors = config.colors === 'variable' ? config.minColors : (config.colors || 0);
        const colors = Array.from({ length: numColors }, (_, i) =>
            (config.defaultColors && config.defaultColors[i]) || [255, 102, 0]
        );
        const params = {
            colors,
            duration_ms: config.params.duration ? config.params.duration.default : 1000
        };
        if (config.params) {
            Object.keys(config.params).forEach(k => {
                if (k !== 'duration' && config.params[k].default !== undefined) {
                    params[k] = config.params[k].default;
                }
            });
        }

        if (!this._effect.steps) this._effect.steps = [];
        this._effect.steps.push({
            step_id: `step_${Date.now()}`,
            effect_type: effectType,
            params
        });

        this._render();
        this._notifyChange();
        if (typeof showNotification === 'function') showNotification('Step added', 'success');
    }

    /** Remove step at index. */
    deleteStep(index) {
        if (!this._effect || !this._effect.steps) return;
        this._effect.steps.splice(index, 1);
        this._render();
        this._notifyChange();
        if (typeof showNotification === 'function') showNotification('Step deleted', 'success');
    }

    /** Clear the container with placeholder text. */
    clear() {
        this._effect = null;
        const container = document.getElementById(this._stepsContainerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center text-white/40 py-8">
                    <span class="material-symbols-outlined text-4xl mb-2 block opacity-50">edit_off</span>
                    <p>Nessun effetto selezionato</p>
                </div>`;
        }
    }

    // ── Private ──────────────────────────────────────────────────────────────

    _render() {
        const container = document.getElementById(this._stepsContainerId);
        if (!container) return;

        container.innerHTML = '';

        if (!this._effect || !this._effect.steps || this._effect.steps.length === 0) {
            container.innerHTML = `
                <div class="text-center text-white/40 py-8">
                    <p>No steps yet. Add your first step!</p>
                </div>`;
            this._scheduleTimelineUpdate();
            return;
        }

        this._effect.steps.forEach((step, index) => {
            container.appendChild(this._createStepCard(step, index));
        });

        this._setupDragAndDrop();
        this._scheduleTimelineUpdate();

        if (window.i18n && window.i18n.apply) window.i18n.apply();
    }

    _createStepCard(step, index) {
        const self = this;   // captured for closures

        const card = document.createElement('div');
        card.className = 'step-card p-4 bg-black/60 border border-[var(--primary-accent)]/30 rounded';
        card.dataset.stepIndex = index;

        const effectType = step.effect_type;
        const duration   = step.params.duration_ms;
        const colors     = step.params.colors || [[255, 102, 0]];

        const formatDuration = ms => ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;

        const colorPickersHTML = this._generateColorPickersHTML(effectType, colors);
        const extraParamsHTML  = this._generateExtraParamsHTML(effectType, step.params);

        card.innerHTML = `
            <div class="flex items-center gap-3 mb-4">
                <div class="drag-handle flex items-center justify-center w-6 -ml-2 cursor-grab hover:bg-white/5 rounded transition-colors" title="Drag to reorder">
                    <span class="material-symbols-outlined text-white/40 text-lg">drag_indicator</span>
                </div>
                <div class="step-number flex items-center justify-center min-w-[32px] px-3 py-1 rounded-md bg-[var(--primary-accent)] text-white orbitron font-bold text-sm">
                    ${index + 1}
                </div>
                <div class="flex-1">
                    <select class="step-type w-full bg-black/60 border border-white/10 text-white rounded p-2 text-sm">
                        ${this._effectTypes.map(t => `
                            <option value="${t.value}" ${t.value === effectType ? 'selected' : ''}>${t.label}</option>
                        `).join('')}
                    </select>
                </div>
                <button class="btn-delete-step p-2 hover:bg-red-500/20 rounded transition-colors" title="Delete Step">
                    <span class="material-symbols-outlined text-sm text-red-400">close</span>
                </button>
            </div>
            <div class="pl-10">
                ${colorPickersHTML}
                <div class="mb-4">
                    <div class="flex items-center justify-between mb-2">
                        <label class="text-xs text-white/55 uppercase">Duration</label>
                        <span class="duration-label text-sm font-bold text-[var(--primary-accent)] orbitron">${formatDuration(duration)}</span>
                    </div>
                    <div class="flex items-center gap-3 mb-2">
                        <input class="duration-slider flex-1" type="range" min="100" max="10000" step="100" value="${duration}" />
                        <input class="step-duration w-20 bg-black/60 border border-[var(--primary-accent)]/50 text-white text-center rounded p-2 text-sm" type="number" min="100" max="10000" step="100" value="${duration}" />
                    </div>
                    <div class="flex gap-2">
                        <button class="preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded" data-duration="250">250ms</button>
                        <button class="preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded" data-duration="500">500ms</button>
                        <button class="preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded" data-duration="1000">1s</button>
                        <button class="preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded" data-duration="2000">2s</button>
                    </div>
                </div>
                ${extraParamsHTML}
            </div>`;

        // ── Delete step ─────────────────────────────────────────────────────
        card.querySelector('.btn-delete-step').addEventListener('click', () => {
            self.deleteStep(index);
        });

        // ── Color pickers ────────────────────────────────────────────────────
        const colorBtns   = card.querySelectorAll('.step-color-btn');
        const colorInputs = card.querySelectorAll('.step-color');

        colorBtns.forEach((colorBtn, colorIndex) => {
            colorBtn.addEventListener('click', function () {
                const colorInput = colorInputs[colorIndex];
                if (typeof openColorPicker === 'function') {
                    openColorPicker(colorInput.value, newColor => {
                        colorInput.value = newColor;
                        colorBtn.style.background = newColor;
                        colorBtn.dataset.color = newColor;
                        if (self._effect && self._effect.steps && self._effect.steps[index]) {
                            const rgb = hexToRgb(newColor);
                            if (!self._effect.steps[index].params.colors) {
                                self._effect.steps[index].params.colors = [];
                            }
                            self._effect.steps[index].params.colors[colorIndex] = rgb || [255, 102, 0];
                        }
                        self._scheduleTimelineUpdate();
                    });
                }
            });
        });

        // ── Add/Remove/Rainbow for Color Cycle ───────────────────────────────
        const btnAddColor = card.querySelector('.btn-add-color');
        if (btnAddColor) {
            btnAddColor.addEventListener('click', () => {
                if (!self._effect || !self._effect.steps || !self._effect.steps[index]) return;
                const stepData = self._effect.steps[index];
                const config = EFFECT_TYPE_CONFIG[stepData.effect_type];
                if (config && config.colors === 'variable' && stepData.params.colors.length < config.maxColors) {
                    stepData.params.colors.push([255, 102, 0]);
                    self._render();
                    self._scheduleTimelineUpdate();
                }
            });
        }

        const btnRemoveColor = card.querySelector('.btn-remove-color');
        if (btnRemoveColor) {
            btnRemoveColor.addEventListener('click', () => {
                if (!self._effect || !self._effect.steps || !self._effect.steps[index]) return;
                const stepData = self._effect.steps[index];
                const config = EFFECT_TYPE_CONFIG[stepData.effect_type];
                if (config && config.colors === 'variable' && stepData.params.colors.length > config.minColors) {
                    stepData.params.colors.pop();
                    self._render();
                    self._scheduleTimelineUpdate();
                }
            });
        }

        const btnRainbow = card.querySelector('.btn-rainbow-preset');
        if (btnRainbow) {
            btnRainbow.addEventListener('click', () => {
                if (!self._effect || !self._effect.steps || !self._effect.steps[index]) return;
                self._effect.steps[index].params.colors = [
                    [255, 0, 0], [255, 127, 0], [255, 255, 0],
                    [0, 255, 0], [0, 0, 255], [75, 0, 130], [148, 0, 211]
                ];
                self._render();
                self._scheduleTimelineUpdate();
            });
        }

        // ── Duration controls ────────────────────────────────────────────────
        const durationSlider  = card.querySelector('.duration-slider');
        const durationInput   = card.querySelector('.step-duration');
        const durationLabel   = card.querySelector('.duration-label');
        const presetButtons   = card.querySelectorAll('.preset-btn[data-duration]');

        const syncDuration = value => {
            const n = parseInt(value);
            if (durationSlider) durationSlider.value = Math.min(Math.max(n, 100), 10000);
            if (durationInput)  durationInput.value  = n;
            if (durationLabel)  durationLabel.textContent = formatDuration(n);
            presetButtons.forEach(btn => btn.classList.toggle('active', parseInt(btn.dataset.duration) === n));
            if (self._effect && self._effect.steps && self._effect.steps[index]) {
                self._effect.steps[index].params.duration_ms = n;
            }
            self._scheduleTimelineUpdate();
        };
        syncDuration(duration);

        const throttledDuration = throttle(v => syncDuration(v), 75);
        if (durationSlider) durationSlider.addEventListener('input', function () { throttledDuration(this.value); });
        if (durationInput)  durationInput.addEventListener('input',  function () { throttledDuration(this.value); });
        presetButtons.forEach(btn => btn.addEventListener('click', function (e) {
            e.preventDefault();
            syncDuration(this.dataset.duration);
        }));

        // ── Extra params sliders ─────────────────────────────────────────────
        card.querySelectorAll('.param-extra-slider').forEach(slider => {
            const paramKey    = slider.dataset.param;
            const numberInput = card.querySelector(`.param-extra[data-param="${paramKey}"]`);
            if (!numberInput) return;
            const syncExtra = value => {
                const n = parseFloat(value);
                slider.value = n;
                numberInput.value = n;
                if (self._effect && self._effect.steps && self._effect.steps[index]) {
                    self._effect.steps[index].params[paramKey] = n;
                }
            };
            const throttledExtra = throttle(syncExtra, 75);
            slider.addEventListener('input', function () { throttledExtra(this.value); });
            numberInput.addEventListener('input', function () { throttledExtra(this.value); });
        });

        // ── Direction grid ───────────────────────────────────────────────────
        const paramDirection = card.querySelector('.param-direction');
        card.querySelectorAll('.dir-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                if (this.disabled) return;
                const val = this.dataset.value;
                if (paramDirection) paramDirection.value = val;
                if (self._effect && self._effect.steps && self._effect.steps[index]) {
                    self._effect.steps[index].params.direction = val;
                }
                card.querySelectorAll('.dir-btn').forEach(b => b.classList.toggle('active', b.dataset.value === val));
            });
        });

        // ── Keyboard preset buttons ──────────────────────────────────────────
        const kbdPresetBtns   = card.querySelectorAll('.kbd-preset-btn');
        const kbdFillPicker   = card.querySelector('.kbd-fill-picker');
        const kbdFillColorBtn = card.querySelector('.kbd-fill-color-btn');
        const kbdFillColorVal = card.querySelector('.kbd-fill-color-val');
        const kbdFillHexLabel = card.querySelector('.kbd-fill-hex-label');

        kbdPresetBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const val = this.dataset.value;
                if (paramDirection) paramDirection.value = val;
                if (self._effect && self._effect.steps && self._effect.steps[index]) {
                    self._effect.steps[index].params.direction = val;
                    if (val !== 'fill') {
                        self._effect.steps[index].params.colors = [];
                    }
                }
                kbdPresetBtns.forEach(b => b.classList.toggle('active', b.dataset.value === val));
                if (kbdFillPicker) kbdFillPicker.classList.toggle('hidden', val !== 'fill');
            });
        });

        if (kbdFillColorBtn && kbdFillColorVal) {
            kbdFillColorBtn.addEventListener('click', () => {
                openColorPicker(kbdFillColorVal.value, newHex => {
                    kbdFillColorVal.value = newHex;
                    kbdFillColorBtn.style.background = newHex;
                    if (kbdFillHexLabel) kbdFillHexLabel.textContent = newHex.toUpperCase();
                    if (self._effect && self._effect.steps && self._effect.steps[index]) {
                        const rgb = hexToRgb(newHex);
                        if (rgb) self._effect.steps[index].params.colors = [rgb];
                    }
                });
            });
        }

        // ── Speed slider ─────────────────────────────────────────────────────
        const paramSpeed       = card.querySelector('.param-speed');
        const paramSpeedSlider = card.querySelector('.param-speed-slider');
        const paramSpeedLabel  = card.querySelector('.param-speed-label');

        if (paramSpeed) {
            const speedMin  = parseFloat(paramSpeed.min) || 0.1;
            const speedMax  = parseFloat(paramSpeed.max) || 10.0;
            const speedStep = parseFloat(paramSpeed.step) || 0.1;

            const applySpeed = raw => {
                const val     = Math.max(speedMin, Math.min(speedMax, parseFloat(raw) || speedMin));
                const rounded = Math.round(val / speedStep) * speedStep;
                const display = rounded.toFixed(1);
                paramSpeed.value = display;
                if (paramSpeedSlider) paramSpeedSlider.value = display;
                if (paramSpeedLabel) {
                    const sfx = paramSpeedLabel.dataset.suffix !== undefined ? paramSpeedLabel.dataset.suffix : 'x';
                    paramSpeedLabel.textContent = `${display}${sfx}`;
                }
                if (self._effect && self._effect.steps && self._effect.steps[index]) {
                    self._effect.steps[index].params.speed = rounded;
                }
            };
            const throttledSpeed = throttle(applySpeed, 75);
            paramSpeed.addEventListener('input', function () { throttledSpeed(this.value); });
            if (paramSpeedSlider) paramSpeedSlider.addEventListener('input', function () { throttledSpeed(this.value); });
        }

        // ── Num loops slider ─────────────────────────────────────────────────
        const paramNumLoops = card.querySelector('.param-num-loops');
        if (paramNumLoops) {
            const loopsSlider = card.querySelector('.param-num-loops-slider');
            const loopsLabel  = card.querySelector('.param-num-loops-label');
            const loopsMin    = parseInt(paramNumLoops.min) || 1;
            const loopsMax    = parseInt(paramNumLoops.max) || 50;

            const applyLoops = raw => {
                const val = Math.max(loopsMin, Math.min(loopsMax, parseInt(raw) || loopsMin));
                paramNumLoops.value = val;
                if (loopsSlider) loopsSlider.value = val;
                if (loopsLabel)  loopsLabel.textContent = `${val}x`;
                if (self._effect && self._effect.steps && self._effect.steps[index]) {
                    self._effect.steps[index].params.num_loops = val;
                }
                self._scheduleTimelineUpdate();
            };
            const throttledLoops = throttle(applyLoops, 75);
            paramNumLoops.addEventListener('input', function () { throttledLoops(this.value); });
            if (loopsSlider) loopsSlider.addEventListener('input', function () { throttledLoops(this.value); });
        }

        // ── Fade-in preset buttons ────────────────────────────────────────────
        const paramFadeInMs = card.querySelector('.param-fade-in-ms');
        card.querySelectorAll('.param-fade-preset').forEach(btn => {
            btn.addEventListener('click', function () {
                const val = parseInt(this.dataset.fade, 10);
                if (paramFadeInMs) paramFadeInMs.value = val;
                card.querySelectorAll('.param-fade-preset').forEach(b =>
                    b.classList.toggle('active', parseInt(b.dataset.fade, 10) === val)
                );
                if (self._effect && self._effect.steps && self._effect.steps[index]) {
                    self._effect.steps[index].params.fade_in_ms = val;
                    self._scheduleTimelineUpdate();
                }
            });
        });

        // ── Effect type change ────────────────────────────────────────────────
        const typeSelect = card.querySelector('.step-type');
        if (typeSelect) {
            typeSelect.addEventListener('change', function () {
                const newType = this.value;
                if (!self._effect || !self._effect.steps || !self._effect.steps[index]) return;
                const stepData  = self._effect.steps[index];
                const newConfig = EFFECT_TYPE_CONFIG[newType];

                stepData.effect_type = newType;
                if (newConfig) {
                    const nc = newConfig.colors === 'variable' ? newConfig.minColors : (newConfig.colors || 0);
                    stepData.params.colors = Array.from({ length: nc }, (_, i) =>
                        (newConfig.defaultColors && newConfig.defaultColors[i]) || [255, 102, 0]
                    );
                    if (newConfig.params.duration) stepData.params.duration_ms = newConfig.params.duration.default;
                    Object.keys(newConfig.params).forEach(k => {
                        if (k !== 'duration' && newConfig.params[k].default !== undefined) {
                            stepData.params[k] = newConfig.params[k].default;
                        }
                    });
                }
                self._render();
                self._scheduleTimelineUpdate();
            });
        }

        return card;
    }

    _setupDragAndDrop() {
        if (this._dragAbortCtrl) this._dragAbortCtrl.abort();
        this._dragAbortCtrl = new AbortController();
        const { signal } = this._dragAbortCtrl;
        const self = this;

        const stepsContainer = document.getElementById(this._stepsContainerId);
        if (!stepsContainer) return;

        const stepCards = stepsContainer.querySelectorAll('.step-card');
        let draggedElement = null;

        document.addEventListener('mouseup', function () {
            stepsContainer.querySelectorAll('.step-card').forEach(c => c.setAttribute('draggable', 'false'));
        }, { signal });

        stepCards.forEach(card => {
            const dragHandle = card.querySelector('.drag-handle');
            if (!dragHandle) return;

            dragHandle.addEventListener('mousedown', function () {
                card.setAttribute('draggable', 'true');
            }, { signal });

            card.addEventListener('dragstart', function (e) {
                draggedElement = this;
                this.style.opacity = '0.5';
                e.dataTransfer.effectAllowed = 'move';
                dragHandle.style.cursor = 'grabbing';
            }, { signal });

            card.addEventListener('dragend', function () {
                this.style.opacity = '';
                dragHandle.style.cursor = 'grab';
                stepsContainer.querySelectorAll('.step-card').forEach(c => {
                    c.classList.remove('border-[var(--primary-accent)]');
                    c.style.borderWidth = '';
                });
            }, { signal });

            card.addEventListener('dragover', function (e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                if (draggedElement !== this) {
                    this.classList.add('border-[var(--primary-accent)]');
                    this.style.borderWidth = '2px';
                }
            }, { signal });

            card.addEventListener('dragleave', function () {
                this.classList.remove('border-[var(--primary-accent)]');
                this.style.borderWidth = '';
            }, { signal });

            card.addEventListener('drop', function (e) {
                e.preventDefault();
                if (draggedElement !== this) {
                    const allCards     = Array.from(stepsContainer.querySelectorAll('.step-card'));
                    const draggedIndex = allCards.indexOf(draggedElement);
                    const targetIndex  = allCards.indexOf(this);

                    if (draggedIndex < targetIndex) {
                        this.parentNode.insertBefore(draggedElement, this.nextSibling);
                    } else {
                        this.parentNode.insertBefore(draggedElement, this);
                    }

                    // Update step number badges
                    stepsContainer.querySelectorAll('.step-card').forEach((c, i) => {
                        c.dataset.stepIndex = i;
                        const badge = c.querySelector('.step-number');
                        if (badge) badge.textContent = i + 1;
                    });

                    // Sync in-memory order
                    if (self._effect && self._effect.steps) {
                        const moved = self._effect.steps.splice(draggedIndex, 1)[0];
                        self._effect.steps.splice(targetIndex, 0, moved);
                    }

                    self._scheduleTimelineUpdate();
                }
                this.classList.remove('border-[var(--primary-accent)]');
                this.style.borderWidth = '';
            }, { signal });
        });
    }

    _scheduleTimelineUpdate() {
        if (this._timelineTimer !== null) clearTimeout(this._timelineTimer);
        this._timelineTimer = setTimeout(() => {
            this._timelineTimer = null;
            this._renderTimeline();
            if (this._onStepsChange) this._onStepsChange(this._collectSteps());
        }, 50);
    }

    _renderTimeline() {
        if (!this._timelineCanvasId) {
            // Fall back to page-level renderColorTimeline if present
            if (typeof renderColorTimeline === 'function') renderColorTimeline();
            return;
        }
        const canvas = document.getElementById(this._timelineCanvasId);
        if (!canvas) return;

        const ctx    = canvas.getContext('2d');
        const width  = canvas.width = canvas.offsetWidth;
        const height = canvas.height;
        ctx.clearRect(0, 0, width, height);

        const container = document.getElementById(this._stepsContainerId);
        if (!container) return;

        const steps = [];
        container.querySelectorAll('.step-card').forEach(card => {
            const durationInput = card.querySelector('.step-duration');
            const colorInputs   = card.querySelectorAll('.step-color');
            if (!durationInput || colorInputs.length === 0) return;
            const colors = Array.from(colorInputs).map(inp =>
                inp.value && inp.value.startsWith('#') ? inp.value : '#0055FF'
            );
            steps.push({ duration: parseInt(durationInput.value) || 500, colors });
        });

        if (steps.length === 0) return;

        const totalDuration = steps.reduce((s, st) => s + st.duration, 0);
        const padding = 0;
        let x = padding;

        steps.forEach(st => {
            const w = ((st.duration / totalDuration) * (width - padding * 2));
            const grad = ctx.createLinearGradient(x, 0, x + w, 0);
            st.colors.forEach((c, i) => {
                grad.addColorStop(i / Math.max(st.colors.length - 1, 1), c);
            });
            ctx.fillStyle = grad;
            ctx.fillRect(x, 0, w, height);
            x += w;
        });
    }

    /** Collect current step data from DOM (like collectFormData but steps only). */
    _collectSteps() {
        const steps = [];
        const container = document.getElementById(this._stepsContainerId);
        if (!container) return steps;

        container.querySelectorAll('.step-card').forEach((card, index) => {
            const effectType = card.querySelector('.step-type') ? card.querySelector('.step-type').value : 'static_transition';
            const duration   = parseInt((card.querySelector('.step-duration') || {}).value) || 1000;

            const colorInputs = card.querySelectorAll('.step-color');
            const colors = [];
            colorInputs.forEach(inp => {
                const rgb = hexToRgb(inp.value);
                colors.push(rgb || [255, 102, 0]);
            });

            const params = { colors, duration_ms: duration };

            const paramDirection = card.querySelector('.param-direction');
            if (paramDirection) {
                params.direction = paramDirection.value;
                if (paramDirection.value === 'fill') {
                    const fillVal = card.querySelector('.kbd-fill-color-val');
                    if (fillVal) {
                        const rgb = hexToRgb(fillVal.value);
                        if (rgb) params.colors = [rgb];
                    }
                }
            }

            const paramSpeed = card.querySelector('.param-speed');
            if (paramSpeed) params.speed = parseFloat(paramSpeed.value);

            const paramNumLoops = card.querySelector('.param-num-loops');
            if (paramNumLoops) params.num_loops = parseInt(paramNumLoops.value);

            card.querySelectorAll('.param-extra').forEach(inp => {
                if (inp.dataset.param) params[inp.dataset.param] = parseFloat(inp.value);
            });

            const paramFadeInMs = card.querySelector('.param-fade-in-ms');
            if (paramFadeInMs) params.fade_in_ms = parseInt(paramFadeInMs.value, 10) || 0;

            steps.push({ step_id: `step_${index}`, effect_type: effectType, params });
        });

        return steps;
    }

    _notifyChange() {
        if (this._onStepsChange) this._onStepsChange(this._collectSteps());
    }

    // ── Static HTML helpers ──────────────────────────────────────────────────

    _generateColorPickersHTML(effectType, colors) {
        const config = EFFECT_TYPE_CONFIG[effectType];
        if (!config) return '';

        const numColors = config.colors === 'variable' ? colors.length : (config.colors || 0);
        if (numColors === 0) return '';

        const labels = config.colorLabels || [];
        let gridClass = 'grid gap-4';
        if (numColors === 1)      gridClass += ' grid-cols-1';
        else if (numColors === 2) gridClass += ' grid-cols-2';
        else if (numColors === 4) gridClass += ' grid-cols-2';
        else if (numColors === 5) gridClass += ' grid-cols-5';
        else                      gridClass += ' grid-cols-3';

        let html = `<div class="${gridClass} mb-4">`;
        for (let i = 0; i < numColors; i++) {
            const color    = colors[i] || (config.defaultColors && config.defaultColors[i]) || [255, 102, 0];
            const colorHex = rgbToHex(color[0], color[1], color[2]);
            const label    = labels[i] || `Color ${i + 1}`;
            html += `
                <div class="color-picker-wrapper">
                    <label class="block text-xs text-white/55 uppercase mb-2">${label}</label>
                    <button class="step-color-btn w-full h-12 rounded cursor-pointer border-2 border-[var(--primary-accent)]/50 hover:border-[var(--primary-accent)] transition-all"
                            style="background: ${colorHex};"
                            data-color="${colorHex}" data-color-index="${i}"
                            title="Click to change color"></button>
                    <input type="hidden" class="step-color" data-color-index="${i}" value="${colorHex}">
                </div>`;
        }
        html += '</div>';

        if (config.colors === 'variable') {
            const canAdd    = numColors < config.maxColors;
            const canRemove = numColors > config.minColors;
            html += `<div class="flex gap-2 mb-4">
                <button class="btn-rainbow-preset preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">palette</span> Rainbow
                </button>
                ${canAdd    ? `<button class="btn-add-color preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded">+ Add Color</button>` : ''}
                ${canRemove ? `<button class="btn-remove-color px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-sm transition-colors">Remove</button>` : ''}
            </div>`;
        }
        return html;
    }

    _generateExtraParamsHTML(effectType, params) {
        const config = EFFECT_TYPE_CONFIG[effectType];
        if (!config || !config.params) return '';

        const hasDirection = !!config.params.direction;
        const hasSpeed     = !!config.params.speed;
        const hasNumLoops  = !!config.params.num_loops;
        const hasSliders   = hasSpeed || hasNumLoops;

        const STANDARD = new Set(['duration', 'direction', 'speed', 'num_loops', 'loop_infinite', 'fade_in_ms']);
        const extraEntries = Object.entries(config.params)
            .filter(([key, cfg]) => !STANDARD.has(key) && cfg.type === 'number');
        const hasExtra = extraEntries.length > 0;

        // Fade-in
        const hasFadeIn = config.canFadeIn === true;
        const FADE_PRESETS = [
            { value: 0, label: 'Off' }, { value: 150, label: 'Fast' },
            { value: 400, label: 'Med' }, { value: 800, label: 'Slow' }
        ];
        let fadeInHTML = '';
        if (hasFadeIn) {
            const currentFadeMs = params.fade_in_ms != null ? params.fade_in_ms : 0;
            const btns = FADE_PRESETS.map(p => `
                <button type="button" class="preset-btn px-3 py-1 text-xs uppercase tracking-wider rounded param-fade-preset ${p.value === currentFadeMs ? 'active' : ''}" data-fade="${p.value}">${p.label}</button>`
            ).join('');
            fadeInHTML = `<div class="mt-4">
                <label class="block text-xs text-white/55 uppercase tracking-wider mb-2">Fade-In</label>
                <div class="flex gap-2">${btns}</div>
                <input type="hidden" class="param-fade-in-ms" value="${currentFadeMs}" />
            </div>`;
        }

        // Keyboard preset
        if (config.hasKeyboardPreset) {
            const currentPreset = params.direction || '1';
            const isFill = currentPreset === 'fill';
            const fillRgb = (params.colors && params.colors[0]) ? params.colors[0] : [255, 102, 0];
            const fillHex = '#' + fillRgb.map(v => (v || 0).toString(16).padStart(2, '0')).join('');
            const opts = [
                { id: '1', label: 'P1' }, { id: '2', label: 'P2' },
                { id: '3', label: 'P3' }, { id: 'fill', label: 'Fill' }
            ];
            const presetBtns = opts.map(opt => `
                <button type="button" class="kbd-preset-btn flex-1 preset-btn py-2 orbitron text-xs tracking-wider rounded ${opt.id === currentPreset ? 'active' : ''}" data-value="${opt.id}">${opt.label}</button>`
            ).join('');
            return `<div class="mt-4">
                <label class="block text-xs text-white/55 uppercase tracking-wider mb-2">Keyboard Preset</label>
                <div class="flex gap-2 mb-3">${presetBtns}</div>
                <input type="hidden" class="param-direction" value="${currentPreset}" />
                <div class="kbd-fill-picker flex items-center gap-2 ${isFill ? '' : 'hidden'}">
                    <label class="text-xs text-white/55 flex-shrink-0">Color:</label>
                    <button type="button" class="kbd-fill-color-btn w-7 h-5 rounded border border-white/20 hover:border-[var(--primary-accent)]/60 flex-shrink-0" style="background:${fillHex}"></button>
                    <input type="hidden" class="kbd-fill-color-val" value="${fillHex}" />
                    <span class="text-xs text-white/55 font-mono kbd-fill-hex-label">${fillHex.toUpperCase()}</span>
                </div>
            </div>`;
        }

        // Direction grid
        let dirHTML = '';
        if (hasDirection) {
            const currentDir = params.direction || config.params.direction.default;
            const DIR_ICONS  = {
                tl: 'north_west', top: 'north', tr: 'north_east',
                left: 'west', right: 'east',
                bl: 'south_west', down: 'south', br: 'south_east'
            };
            const DIR_LAYOUT = [['tl','top','tr'], ['left',null,'right'], ['bl','down','br']];
            const allowedDirs = config.directionOptions || null;
            const gridCells = DIR_LAYOUT.map(row => row.map(val => {
                if (val === null) return '<div></div>';
                const isActive   = val === currentDir;
                const isDisabled = allowedDirs && !allowedDirs.includes(val);
                return `<button type="button" class="dir-btn preset-btn flex items-center justify-center w-8 h-8 rounded ${isActive ? 'active' : ''} ${isDisabled ? 'opacity-20 grayscale cursor-not-allowed pointer-events-none' : ''}" data-value="${val}" ${isDisabled ? 'disabled' : ''}>
                    <span class="material-symbols-outlined text-base">${DIR_ICONS[val]}</span>
                </button>`;
            }).join('')).join('');
            dirHTML = `<div>
                <label class="block text-xs text-white/55 uppercase mb-2">Direction</label>
                <div class="inline-grid grid-cols-3 gap-1">${gridCells}</div>
                <input type="hidden" class="param-direction" value="${currentDir}" />
            </div>`;
        }

        // Speed slider
        let speedHTML = '';
        if (hasSpeed) {
            const cfg         = config.params.speed;
            const currentSpeed = params.speed != null ? params.speed : cfg.default;
            const sfx         = cfg.suffix !== undefined ? cfg.suffix : 'x';
            speedHTML = `<div>
                <div class="flex items-center justify-between mb-2">
                    <label class="text-xs text-white/55 uppercase">${cfg.label || 'Speed'}</label>
                    <span class="param-speed-label text-sm font-bold text-[var(--primary-accent)] orbitron" data-suffix="${sfx}">${currentSpeed}${sfx}</span>
                </div>
                <div class="flex items-center gap-3">
                    <input class="param-speed-slider flex-1" type="range" min="${cfg.min}" max="${cfg.max}" step="${cfg.step || 0.1}" value="${currentSpeed}" />
                    <input class="param-speed w-20 bg-black/60 border border-[var(--primary-accent)]/50 text-white text-center rounded p-2 text-sm" type="number" min="${cfg.min}" max="${cfg.max}" step="${cfg.step || 0.1}" value="${currentSpeed}" />
                </div>
            </div>`;
        }

        // Num loops slider
        let loopsHTML = '';
        if (hasNumLoops) {
            const cfg          = config.params.num_loops;
            const currentLoops = params.num_loops != null ? params.num_loops : cfg.default;
            loopsHTML = `<div>
                <div class="flex items-center justify-between mb-2">
                    <label class="text-xs text-white/55 uppercase">${cfg.label || 'Loops'}</label>
                    <span class="param-num-loops-label text-sm font-bold text-[var(--primary-accent)] orbitron">${currentLoops}x</span>
                </div>
                <div class="flex items-center gap-3">
                    <input class="param-num-loops-slider duration-slider flex-1" type="range" min="${cfg.min ?? 1}" max="${cfg.max ?? 50}" step="1" value="${currentLoops}" />
                    <input class="param-num-loops w-20 bg-black/60 border border-[var(--primary-accent)]/50 text-white text-center rounded p-2 text-sm" type="number" min="${cfg.min ?? 1}" max="${cfg.max ?? 50}" value="${currentLoops}" />
                </div>
            </div>`;
        }

        // Extra numeric params
        let extraHTML = '';
        if (hasExtra) {
            const cells = extraEntries.map(([key, cfg]) => {
                const current = params[key] != null ? params[key] : cfg.default;
                const step    = cfg.step || 1;
                return `<div>
                    <label class="block text-xs text-white/55 uppercase mb-1">${cfg.label}</label>
                    <div class="flex items-center gap-3">
                        <input class="param-extra-slider flex-1" type="range" min="${cfg.min}" max="${cfg.max}" step="${step}" value="${current}" data-param="${key}" />
                        <input class="param-extra w-20 bg-black/60 border border-[var(--primary-accent)]/50 text-white text-center rounded p-2 text-sm" type="number" min="${cfg.min}" max="${cfg.max}" step="${step}" value="${current}" data-param="${key}" />
                    </div>
                </div>`;
            }).join('');
            const gridCls = extraEntries.length <= 2
                ? 'grid grid-cols-1 md:grid-cols-2 gap-2'
                : 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-2';
            extraHTML = `<div class="${gridCls}">${cells}</div>`;
        }

        const rightContent = speedHTML + loopsHTML + extraHTML;
        const hasRight = hasSliders || hasExtra;

        let finalHTML = '';
        if (hasDirection && hasRight) {
            finalHTML = `<div class="grid grid-cols-2 gap-4 mt-4">${dirHTML}<div class="flex flex-col gap-3">${rightContent}</div></div>`;
        } else if (hasDirection) {
            finalHTML = `<div class="mt-4">${dirHTML}</div>`;
        } else if (hasExtra && !hasSliders) {
            finalHTML = `<div class="mt-4">${extraHTML}</div>`;
        } else if (hasRight) {
            finalHTML = `<div class="flex flex-col gap-3 mt-4">${rightContent}</div>`;
        }
        if (hasFadeIn) finalHTML += fadeInHTML;

        return finalHTML;
    }
}

// ── Global exports ───────────────────────────────────────────────────────────
window.EFFECT_TYPE_CONFIG  = EFFECT_TYPE_CONFIG;
window.EffectEditorModule  = EffectEditorModule;
