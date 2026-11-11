/**
 * effects.js
 * Effects Editor page logic
 *
 * Handles:
 * - Effects list loading
 * - Effect CRUD operations
 * - Step sequencer UI
 * - Effect testing on devices
 */

// ========================================
// STATE
// ========================================

let effectsList      = [];
let effectsListFull  = [];   // unfiltered — all effects from API
let _libCategory     = null; // null = all, 'event', 'status', 'general'
let _libSearchQuery  = '';   // search query for filtering effects by name
let filterShowOnlyNew = false; // Filter: show only quick-created effects
let currentEffect    = null;
let _editorModule    = null; // EffectEditorModule instance
let isEditing        = false;

// Reconnection state tracking (Tier 2)
let _isReconnecting = false;  // True when showing reconnect toast


// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', async function () {
    console.log('[Effects] Initializing...');

    // Init the reusable step-editor module (effect-editor-module.js)
    _editorModule = new EffectEditorModule({
        stepsContainerId: 'steps-container',
        timelineCanvasId: null,          // use page-level renderColorTimeline()
        onStepsChange: (steps) => {
            if (currentEffect) currentEffect.steps = steps;
        }
    });
    await _editorModule.init();

    // Load user settings for i18n
    await loadUserSettings();

    // Load effects list
    loadEffectsList();

    // Setup event listeners
    setupEventListeners();

    console.log('[Effects] Initialization complete');
});

// ========================================
// LOAD USER SETTINGS (FOR I18N)
// ========================================

async function loadUserSettings() {
    console.log('[Effects] Loading user settings for i18n...');

    const result = await api('get_settings');

    if (result && result.language) {
        // Initialize i18n with user's language
        if (window.i18n) {
            await window.i18n.init(result.language);
            console.log(`[Effects] i18n initialized with language: ${result.language}`);
        }
    }

    // Trigger fade-in AFTER translations are applied (prevents FOUC)
    requestAnimationFrame(function () {
        document.body.classList.add('loaded');
        console.log('[Effects] Page fade-in triggered (translations ready)');
    });
}

// ========================================
// LOAD EVENT MAPPINGS AND DEFINITIONS
// ========================================



// ========================================
// LOAD METADATA
// ========================================



// ========================================
// EFFECTS LIST
// ========================================

async function loadEffectsList(keepEditor = false) {
    console.log('[Effects] Loading effects list...');

    const result = await api('get_effects_list');

    if (!result || !result.success) {
        showNotification(window.i18n.get('notifications.failed_load_effects') || 'Failed to load effects', 'error');
        console.error('[Effects] Load failed:', result);
        return;
    }

    effectsListFull = result.effects || [];
    _applyLibraryFilter();
    console.log('[Effects] Loaded effects:', effectsListFull.length);

    if (!keepEditor) disableEditorPanel();

    renderEffectsList();

    if (!keepEditor && effectsList.length > 0) {
        await loadEffect(effectsList[0].id);
    } else if (!keepEditor) {
        showNotification(window.i18n.interpolate('notifications.loaded_effects_count', {count: effectsListFull.length}) || `Loaded ${effectsListFull.length} effect(s)`, 'success');
    }
}

/** Apply current category filter + NEW filter + search query to effectsListFull → effectsList. */
function _applyLibraryFilter() {
    let filtered = _libCategory
        ? effectsListFull.filter(e => e.category === _libCategory || e.category === 'general')
        : effectsListFull;

    // Apply "Show Only NEW" filter
    if (filterShowOnlyNew) {
        filtered = filtered.filter(e => e.is_quick_created === true);
    }

    // Apply search query filter (case-insensitive)
    if (_libSearchQuery.trim()) {
        const query = _libSearchQuery.toLowerCase();
        filtered = filtered.filter(e => e.name.toLowerCase().includes(query));
    }

    effectsList = filtered;
    _syncLibraryTabs();
}

/** Highlight the active tab in the library sidebar. */
function _syncLibraryTabs() {
    document.querySelectorAll('.lib-cat-tab').forEach(btn => {
        const active = (btn.dataset.cat || null) === _libCategory;
        btn.classList.toggle('active', active);
    });
}

/**
 * Get list of events associated with an effect_id
 * @param {string} effectId - Effect ID to search for
 * @returns {Array<{name: string, description: string}>} Array of event objects
 */

function renderEffectsList() {
    const container = document.getElementById('effects-list');
    if (!container) { console.warn('[Effects] Container #effects-list not found'); return; }

    container.innerHTML = '';

    if (effectsList.length === 0) {
        container.innerHTML = `<div class="text-center text-white/40 py-8">
            <p>${_libCategory ? window.i18n.interpolate('common.no_effects_in_category', {category: _libCategory}) || `No effects in category "${_libCategory}"` : window.i18n.get('common.no_effects_yet') || 'No effects yet...'}</p></div>`;
        disableEditorPanel();
        return;
    }

    effectsList.forEach(effect => container.appendChild(createEffectCard(effect)));
}

function _generateTimelinePreview(steps, maxSegments = 12) {
    if (!steps || steps.length === 0) {
        return '<div class="timeline-preview"><div class="timeline-segment" style="background: rgba(255,255,255,0.1);"></div></div>';
    }

    // Calculate proportional widths based on duration
    const totalDuration = steps.reduce((sum, s) => sum + (s.params?.duration_ms || 1000), 0);
    const segments = steps.slice(0, maxSegments).map((step, idx) => {
        const duration = step.params?.duration_ms || 1000;
        const widthPercent = ((duration / totalDuration) * 100).toFixed(1);

        // Get first color from step, or default gray
        let color = 'rgba(255, 255, 255, 0.2)';
        if (step.params?.colors && step.params.colors.length > 0) {
            const [r, g, b] = step.params.colors[0];
            color = `rgb(${r}, ${g}, ${b})`;
        }

        return `<div class="timeline-segment" style="flex: ${widthPercent}; background: ${color};" title="Step ${idx + 1}: ${step.effect_type}"></div>`;
    });

    return `<div class="timeline-preview">${segments.join('')}</div>`;
}

function createEffectCard(effect) {
    const card = document.createElement('div');
    const isSpecial = effect.id === 'keyboard_default';
    const isQuickCreated = effect.is_quick_created === true;

    card.className = 'effect-card p-3 bg-black/40 border border-white/10 rounded cursor-pointer hover:border-[var(--primary-accent)]/50';
    card.dataset.effectId = effect.id;

    const stepsCount = effect.steps ? effect.steps.length : 0;
    const category = effect.category || 'custom';

    // Check if last step is already a keyboard effect
    const lastStep = effect.steps && effect.steps.length > 0 ? effect.steps[effect.steps.length - 1] : null;
    const hasKeyboardAsLastStep = lastStep && lastStep.effect_type === 'keyboard_default';

    const categoryBadge = isSpecial
        ? `<span class="text-xs px-1.5 py-0.5 rounded uppercase tracking-wider bg-violet-500/20 text-violet-400">SPECIAL</span>`
        : `<span class="text-xs px-1.5 py-0.5 rounded uppercase tracking-wider bg-white/10 text-white/60">${category}</span>`;

    // NEW badge for quick-created effects
    const newBadge = isQuickCreated
        ? `<span class="text-xs px-1.5 py-0.5 rounded uppercase tracking-wider bg-amber-500/20 text-amber-300 font-bold animate-pulse" style="animation: pulse 2s ease-in-out infinite;">✨ NEW</span>`
        : '';

    // Generate compact timeline preview (max 12 segments)
    const timelineHtml = _generateTimelinePreview(effect.steps || [], 12);

    // Keyboard Default button: disabled if last step is already keyboard effect
    const kdButtonClass = hasKeyboardAsLastStep
        ? 'btn-add-kd-step p-1.5 rounded opacity-30 cursor-not-allowed'
        : 'btn-add-kd-step p-1.5 hover:bg-violet-500/20 rounded';
    const kdIconClass = hasKeyboardAsLastStep
        ? 'material-symbols-outlined text-base text-white/30'
        : 'material-symbols-outlined text-base text-violet-400';
    const kdTitle = hasKeyboardAsLastStep
        ? window.i18n.get('common.keyboard_default_is_last') || 'Last step is already Keyboard Default'
        : window.i18n.get('common.add_keyboard_default') || 'Add Keyboard Default as final step';

    const actionButtons = isSpecial
        ? `<button class="btn-test-effect p-1.5 hover:bg-[var(--primary-accent)]/20 rounded" title="Test Effect">
               <span class="material-symbols-outlined text-base text-[var(--primary-accent)]">play_arrow</span>
           </button>`
        : `<button class="btn-test-effect p-1.5 hover:bg-[var(--primary-accent)]/20 rounded" title="Test Effect">
               <span class="material-symbols-outlined text-base text-[var(--primary-accent)]">play_arrow</span>
           </button>
           <button class="${kdButtonClass}" title="${kdTitle}" ${hasKeyboardAsLastStep ? 'disabled' : ''}>
               <span class="${kdIconClass}">keyboard_return</span>
           </button>
           <button class="btn-delete-effect p-1.5 hover:bg-red-500/20 rounded" title="Delete Effect">
               <span class="material-symbols-outlined text-base text-red-400">delete</span>
           </button>`;

    card.innerHTML = `
        <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <div class="font-bold text-white text-sm truncate">${escapeHtml(effect.name)}</div>
                    ${newBadge}
                </div>
                <div class="flex items-center gap-2 mt-1">
                    <span class="text-xs text-[var(--primary-accent)] font-bold">${stepsCount} STEPS</span>
                    ${categoryBadge}
                </div>
                ${timelineHtml}
            </div>
            <div class="flex gap-1 flex-shrink-0">
                ${actionButtons}
            </div>
        </div>
    `;

    // Click card to edit
    card.addEventListener('click', function (e) {
        if (e.target.closest('button')) return;
        loadEffect(effect.id);
    });

    // Test button
    card.querySelector('.btn-test-effect').addEventListener('click', function (e) {
        e.stopPropagation();
        testEffect(effect.id);
    });

    if (!isSpecial) {
        // Quick add Keyboard Default step
        card.querySelector('.btn-add-kd-step').addEventListener('click', function (e) {
            e.stopPropagation();
            // Ignore click if button is disabled (last step is already keyboard effect)
            if (this.disabled || hasKeyboardAsLastStep) return;
            quickAddKeyboardDefaultStep(effect.id, effect.name);
        });

        // Delete button
        card.querySelector('.btn-delete-effect').addEventListener('click', function (e) {
            e.stopPropagation();
            confirmDeleteEffect(effect.id, effect.name);
        });
    }

    return card;
}

// ========================================
// KEYBOARD DEFAULT SPECIAL HANDLING
// ========================================

async function quickAddKeyboardDefaultStep(effectId, effectName) {
    const r = await api('get_effect', effectId);
    if (!r?.success) { showNotification(window.i18n.get('notifications.save_failed') || 'Could not load effect', 'error'); return; }

    const effect = r.effect;
    // Avoid duplicate: don't add if last step is already keyboard_default
    const lastStep = effect.steps?.at(-1);
    if (lastStep?.effect_type === 'keyboard_default') {
        showNotification(window.i18n.get('notifications.keyboard_default_exists') || 'Already has Keyboard Default step', 'info');
        return;
    }

    effect.steps = effect.steps || [];
    effect.steps.push({
        step_id: `step_${Date.now()}`,
        effect_type: 'keyboard_default',
        params: {
            colors: [], duration_ms: 800, direction: '1',
            speed: null, num_loops: null, loop_infinite: false,
            glitch_percentage: null, glitch_duration_ms: null,
            duration_variability: null, persistence_percentage: null,
            color_variation: null, intensity: null, density: null,
            wave_weights: null, height: null, tail_length: null,
            wave_frequency: null, ripple: null, bolt_interval_ms: null
        }
    });

    const upd = await api('update_effect', effectId, effect);
    if (upd?.success) {
        showNotification(window.i18n.interpolate('notifications.keyboard_default_added', {name: effectName}) || `Keyboard Default step added to "${effectName}"`, 'success');
        // Reload list and re-select current effect if it was open
        await loadEffectsList(true);
        if (currentEffect?.id === effectId) await loadEffect(effectId);
    } else {
        showNotification(upd?.error || window.i18n.get('notifications.save_failed') || 'Failed to update effect', 'error');
    }
}

let _kdConfigPreset = '1';

function showKeyboardDefaultPanel(effect) {
    // Hide the standard editor, show the special config panel
    const editorEl = document.getElementById('effect-editor-content');
    if (editorEl) editorEl.style.display = 'none';

    let panel = document.getElementById('keyboard-default-panel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'keyboard-default-panel';
        panel.className = 'p-6 space-y-6';
        const editorContainer = editorEl?.parentElement;
        if (editorContainer) editorContainer.appendChild(panel);
    }

    panel.style.display = '';

    // Load current config from API
    api('get_keyboard_presets').then(r => {
        _kdConfigPreset = r?.active_preset || '1';
        const lock = r?.lock_keyboard || false;
        _renderKdPanel(panel, _kdConfigPreset, lock, r?.presets || {});
    });
}

function _renderKdPanel(panel, activePreset, lockKb, presets) {
    panel.innerHTML = `
        <div class="flex items-center gap-3 mb-2">
            <span class="material-symbols-outlined text-2xl text-violet-400">keyboard</span>
            <div>
                <div class="orbitron text-sm tracking-wider text-white font-bold">Keyboard Default</div>
                <div class="text-xs text-white/40 mt-0.5">Configure in Keyboard Designer, then select preset</div>
            </div>
        </div>
        <div class="sci-fi-border carbon-pattern p-4 rounded text-xs text-white/50 italic leading-relaxed">
            Use the <a href="keyboard-designer.html" class="text-[var(--primary-accent)] hover:underline">Keyboard Designer</a>
            to paint keys and save them to a preset (P1, P2, P3).
            This effect will apply the selected preset with a soft transition.
        </div>

        <div>
            <div class="orbitron text-xs tracking-[0.2em] text-white/50 uppercase mb-3">Active Preset</div>
            <div class="flex gap-3">
                ${['1', '2', '3'].map(id => {
        const p = presets[id] || {};
        const hasData = p.has_data;
        const isActive = String(activePreset) === id;
        return `<button
                        class="kd-preset-btn flex-1 btn-sci-fi py-3 orbitron text-sm tracking-wider transition-all
                               ${isActive ? 'border-violet-400 text-violet-400' : ''}"
                        data-preset="${id}"
                        style="${isActive ? 'border-color:rgba(139,92,246,.7);' : ''}">
                        <div>P${id}</div>
                        <div class="text-[10px] mt-0.5 ${hasData ? 'text-green-400/80' : 'text-white/40'}">
                            ${hasData ? 'configured' : 'empty'}
                        </div>
                    </button>`;
    }).join('')}
            </div>
        </div>

        <div>
            <label class="glass-toggle-container">
                <input id="toggle-kbd-lock" type="checkbox" class="glass-toggle-input" ${lockKb ? 'checked' : ''}/>
                <div class="glass-toggle-track"><div class="glass-toggle-thumb"></div></div>
                <span class="glass-toggle-label text-sm">Lock keyboard during other effects</span>
            </label>
            <p class="text-xs text-white/50 mt-2 ml-14">
                When ON, other effects will not override keyboard colors while this is active.
            </p>
        </div>

        <button id="btn-save-kd-config" class="w-full btn-sci-fi py-3 orbitron text-sm tracking-wider flex items-center justify-center gap-2">
            <span class="material-symbols-outlined text-sm text-[var(--primary-accent)]">save</span>
            SAVE CONFIGURATION
        </button>
    `;

    // Preset button click
    panel.querySelectorAll('.kd-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            _kdConfigPreset = btn.dataset.preset;
            panel.querySelectorAll('.kd-preset-btn').forEach(b => {
                const isNow = b.dataset.preset === _kdConfigPreset;
                b.style.borderColor = isNow ? 'rgba(139,92,246,.7)' : '';
                b.classList.toggle('text-violet-400', isNow);
            });
        });
    });

    // Save config
    panel.querySelector('#btn-save-kd-config').addEventListener('click', async () => {
        const lock = panel.querySelector('#toggle-kbd-lock')?.checked || false;
        const r = await api('save_keyboard_default_config', _kdConfigPreset, lock);
        if (r?.success) showNotification(window.i18n.get('notifications.keyboard_default_config_saved') || 'Keyboard Default configuration saved', 'success');
        else showNotification(r?.error || window.i18n.get('notifications.save_failed') || 'Save failed', 'error');
    });
}

function hideKeyboardDefaultPanel() {
    const panel = document.getElementById('keyboard-default-panel');
    if (panel) panel.style.display = 'none';
    const editorEl = document.getElementById('effect-editor-content');
    if (editorEl) editorEl.style.display = '';
}

// ========================================
// LOAD EFFECT FOR EDITING
// ========================================

async function loadEffect(effectId) {
    console.log('[Effects] Loading effect for editing:', effectId);

    const result = await api('get_effect', effectId);

    if (!result || !result.success) {
        showNotification(window.i18n.get('notifications.save_failed') || 'Failed to load effect', 'error');
        return;
    }

    currentEffect = result.effect;
    isEditing = true;

    // Update visual selection in the list
    document.querySelectorAll('.effect-card').forEach(c => c.classList.remove('selected'));
    const activeCard = document.querySelector(`.effect-card[data-effect-id="${effectId}"]`);
    if (activeCard) {
        activeCard.classList.add('selected');
    }

    hideKeyboardDefaultPanel();
    renderEffectEditor(currentEffect);
    showEditorPanel();

    // Disable ADD STEP for special effects (fixed structure, no extra steps allowed)
    const addStepBtn = document.getElementById('btn-add-step');
    if (addStepBtn) {
        const isSpecial = effectId === 'keyboard_default';
        addStepBtn.disabled = isSpecial;
        addStepBtn.title = isSpecial ? i18n.get('tooltips.fixed_structure') : '';
        addStepBtn.style.opacity = isSpecial ? '0.35' : '';
    }

    if (effectId !== 'keyboard_default') {
        showNotification(`Editing: ${currentEffect.name}`, 'info');
    }
}


function renderEffectEditor(effect) {
    // Enable and populate form fields
    const effectName = document.getElementById('effect-name');
    const effectDescription = document.getElementById('effect-description');
    const effectCategory = document.getElementById('effect-category');

    if (effectName) {
        effectName.value = effect.name;
        effectName.disabled = false;
    }
    if (effectDescription) {
        effectDescription.value = effect.description || '';
        effectDescription.disabled = false;
    }
    if (effectCategory) {
        effectCategory.value = effect.category || 'event';
        effectCategory.disabled = false;
    }
    const catSelect = document.getElementById('effect-category-select');
    if (catSelect) {
        catSelect.value = effect.category || 'event';
        catSelect.disabled = false;
        catSelect.onchange = function () {
            if (effectCategory) effectCategory.value = this.value;
            if (currentEffect) currentEffect.category = this.value;
        };
    }

    // Restore timeline visibility
    const timeline = document.getElementById('colorTimeline');
    if (timeline) {
        timeline.style.opacity = '1';
        timeline.style.filter = 'none';
    }

    // Enable action buttons and restore visual feedback
    const btnSave = document.getElementById('btn-save-effect');
    const btnCancel = document.getElementById('btn-cancel-edit');
    const btnAddStep = document.getElementById('btn-add-step');
    const btnTestEffect = document.getElementById('btn-test-effect');
    const btnStop = document.getElementById('btn-stop-effect');
    const btnRevert = document.getElementById('btn-revert-effect');

    if (btnSave) {
        btnSave.disabled = false;
        btnSave.style.opacity = '1';
        btnSave.style.cursor = 'pointer';
    }
    if (btnCancel) {
        btnCancel.disabled = false;
        btnCancel.style.opacity = '1';
        btnCancel.style.cursor = 'pointer';
    }
    if (btnAddStep) {
        btnAddStep.disabled = false;
        btnAddStep.style.opacity = '1';
        btnAddStep.style.cursor = 'pointer';
    }
    if (btnTestEffect) {
        btnTestEffect.disabled = false;
        btnTestEffect.style.opacity = '1';
        btnTestEffect.style.cursor = 'pointer';
    }
    if (btnStop) {
        btnStop.disabled = false;
        btnStop.style.opacity = '1';
        btnStop.style.cursor = 'pointer';
    }
    // Revert only enabled when editing an existing saved effect
    if (btnRevert) {
        const canRevert = isEditing && effect && effect.id;
        btnRevert.disabled = !canRevert;
        btnRevert.style.opacity = canRevert ? '1' : '0.3';
        btnRevert.style.cursor = canRevert ? 'pointer' : 'not-allowed';
    }

    // Render steps via the editor module
    renderSteps(effect.steps || []);
}


// ========================================
// DRAG AND DROP FUNCTIONALITY
// ========================================

let _dragAbortController = null;




// ========================================
// DYNAMIC UI GENERATION HELPERS
// ========================================

// ========================================
// EFFECT EDITOR ACTIONS
// ========================================

// Step rendering is fully delegated to EffectEditorModule (_editorModule).

function renderSteps(steps) {
    if (_editorModule && currentEffect) {
        _editorModule.loadEffect(currentEffect);
    }
}

function addStep() {
    if (!currentEffect) return;
    if (!currentEffect.steps) currentEffect.steps = [];
    if (_editorModule) _editorModule.addStep();
}

function deleteStep(index) {
    if (_editorModule) _editorModule.deleteStep(index);
}

function createNewEffect() {
    // Inherit the currently active library filter as the default category
    currentEffect = {
        id: null,
        name: 'New Effect',
        description: '',
        category: _libCategory || 'event',
        post_behavior: 'static_color',
        steps: []
    };
    isEditing = false;

    // Auto-add first step (default: static_transition)
    addStep();

    renderEffectEditor(currentEffect);
    showEditorPanel();

    showNotification(window.i18n.get('notifications.creating_effect') || 'Creating new effect', 'info');
}



function collectFormData() {
    const name = document.getElementById('effect-name').value.trim();
    const description = document.getElementById('effect-description').value.trim();
    const category = document.getElementById('effect-category').value;

    if (!name) {
        throw new Error(window.i18n.get('notifications.effect_name_required') || 'Effect name is required');
    }

    // Collect steps via the editor module (reads current DOM state)
    const steps = _editorModule ? _editorModule.getSteps() : [];

    const effectData = {
        id: currentEffect ? currentEffect.id : null,
        name,
        description,
        category,
        post_behavior: 'static_color',
        topology_support: ["1D", "2D"], // All effects work on all devices via renderer fallbacks
        steps,
        is_quick_created: false,  // Remove NEW badge when effect is saved/edited
        created_timestamp: currentEffect ? currentEffect.created_timestamp : null  // Preserve original timestamp
    };

    return effectData;
}

async function saveEffect() {
    const btnSave = document.getElementById('btn-save-effect');
    const originalHTML = btnSave ? btnSave.innerHTML : '';

    try {
        // Show loading state
        if (btnSave) {
            btnSave.disabled = true;
            btnSave.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="material-symbols-outlined" style="animation: spin 1s linear infinite;">progress_activity</span>
                    <span>Saving...</span>
                </div>
            `;
        }

        const effectData = collectFormData();
        console.log('[Effects] Saving effect:', effectData.name);

        let result;
        if (isEditing && effectData.id) {
            // Update existing effect
            result = await api('update_effect', effectData.id, effectData);
        } else {
            // Create new effect
            result = await api('create_effect', effectData);
        }

        if (result && result.success) {
            // For new effects, update the in-memory id so the next Save goes to update_effect
            if (!isEditing && result.id) {
                currentEffect.id = result.id;
                isEditing = true;
            }

            // Show success state temporarily, then restore button (stay on editor)
            if (btnSave) {
                btnSave.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="material-symbols-outlined" style="color: #10b981;">check_circle</span>
                        <span>Saved!</span>
                    </div>
                `;
            }

            showNotification(window.i18n.get('notifications.effect_saved') || 'Effect saved successfully!', 'success');

            // Reload list in background (keepEditor=true keeps panel open and selection intact)
            loadEffectsList(true);

            setTimeout(() => {
                if (btnSave) {
                    btnSave.innerHTML = originalHTML;
                    btnSave.disabled = false;
                }
            }, 800);
        } else {
            // Restore button on error
            if (btnSave) {
                btnSave.innerHTML = originalHTML;
                btnSave.disabled = false;
            }
            showNotification(result?.error || window.i18n.get('notifications.save_failed') || 'Save failed', 'error');
        }
    } catch (error) {
        // Restore button on error
        if (btnSave) {
            btnSave.innerHTML = originalHTML;
            btnSave.disabled = false;
        }
        showNotification(error.message, 'error');
        console.error('[Effects] Save error:', error);
    }
}

// Add spin animation CSS if not exists
if (!document.getElementById('button-spin-animation')) {
    const style = document.createElement('style');
    style.id = 'button-spin-animation';
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

function cancelEdit() {
    currentEffect = null;
    isEditing = false;
    disableEditorPanel();
    hideEditorPanel();
}

// ========================================
// EFFECT TESTING
// ========================================

async function testEffect(effectId) {
    console.log('[Effects] Testing effect:', effectId);

    const result = await api('test_effect_on_devices', effectId);

    if (result && result.success) {
        // Success - check if we were reconnecting
        if (_isReconnecting) {
            window.show_reconnect_success_toast();
            _isReconnecting = false;
        }
        showNotification(window.i18n.get('notifications.testing_on_devices') || 'Testing effect on devices...', 'info');
    } else {
        // Check if reconnecting (Tier 2)
        const errorMsg = result?.error || 'Test failed';
        if (errorMsg.includes('Reconnecting') || errorMsg.includes('reconnect')) {
            window.show_reconnect_toast();
            _isReconnecting = true;  // Set flag
        } else {
            showNotification(errorMsg, 'error');
        }
    }
}

async function testCurrentEffect() {
    if (!currentEffect) {
        showNotification(window.i18n.get('notifications.no_effect_selected') || 'No effect selected', 'warning');
        return;
    }

    // Collect current in-memory state (includes unsaved changes)
    const effectData = collectFormData();
    if (!effectData) return;

    console.log('[Effects] Testing live effect (unsaved changes included)');
    console.log('[Effects] DEBUG - effectData:', JSON.stringify(effectData, null, 2));
    const result = await api('test_effect_live', effectData);

    if (result && result.success) {
        // Success - check if we were reconnecting
        if (_isReconnecting) {
            window.show_reconnect_success_toast();
            _isReconnecting = false;
        }
        showNotification(result.message || window.i18n.get('notifications.testing_on_devices') || 'Testing effect on devices...', 'info');
    } else {
        // Check if reconnecting (Tier 2)
        const errorMsg = result?.error || 'Test failed';
        if (errorMsg.includes('Reconnecting') || errorMsg.includes('reconnect')) {
            window.show_reconnect_toast();
            _isReconnecting = true;  // Set flag
        } else {
            showNotification(errorMsg, 'error');
        }
    }
}

async function revertEffect() {
    if (!currentEffect || !isEditing) {
        showNotification(window.i18n.get('notifications.nothing_to_revert') || 'Nothing to revert', 'warning');
        return;
    }

    const confirmed = confirm(`Revert "${currentEffect.name}" to last saved state? Unsaved changes will be lost.`);
    if (!confirmed) return;

    console.log('[Effects] Reverting effect to saved state:', currentEffect.id);
    await loadEffect(currentEffect.id);
    showNotification(window.i18n.get('notifications.reverted_saved') || 'Reverted to saved state', 'success');
}

async function stopEffect() {
    const result = await api('stop_current_effect');

    if (result && result.success) {
        showNotification(window.i18n.get('notifications.effect_stopped') || 'Effect stopped', 'success');
    }
}

// ========================================
// DELETE EFFECT
// ========================================

function confirmDeleteEffect(effectId, effectName) {
    if (confirm(`Delete effect "${effectName}"?\n\nThis action cannot be undone.`)) {
        deleteEffect(effectId);
    }
}

async function deleteEffect(effectId) {
    console.log('[Effects] Deleting effect:', effectId);

    const result = await api('delete_effect', effectId);

    if (result && result.success) {
        showNotification(window.i18n.get('notifications.effect_deleted') || 'Effect deleted', 'success');
        loadEffectsList();

        // If currently editing this effect, close editor
        if (currentEffect && currentEffect.id === effectId) {
            hideEditorPanel();
        }
    } else {
        showNotification(result?.error || window.i18n.get('notifications.save_failed') || 'Delete failed', 'error');
    }
}

// ========================================
// UI HELPERS
// ========================================

function showEditorPanel() {
    // Current layout: flex 30/70 with editor always visible
    // No need to show/hide panels - they're always displayed side-by-side
    console.log('[Effects] Editor panel shown (layout always visible)');
}

function hideEditorPanel() {
    // Current layout: flex 30/70 with editor always visible
    // Just disable the form when no effect is selected
    console.log('[Effects] Editor panel hidden (disabling form)');
    disableEditorPanel();
}

function disableEditorPanel() {
    // Clear current effect
    currentEffect = null;
    isEditing = false;

    // Clear and disable form fields
    const effectName = document.getElementById('effect-name');
    const effectDescription = document.getElementById('effect-description');
    const effectCategory = document.getElementById('effect-category');

    if (effectName) {
        effectName.value = '';
        effectName.disabled = true;
    }
    if (effectDescription) {
        effectDescription.value = '';
        effectDescription.disabled = true;
    }
    if (effectCategory) {
        effectCategory.value = 'custom';
        effectCategory.disabled = true;
    }

    // Clear steps container
    const stepsContainer = document.getElementById('steps-container');
    if (stepsContainer) {
        stepsContainer.innerHTML = `
            <div class="text-center text-white/40 py-8">
                <span class="material-symbols-outlined text-4xl mb-2 block opacity-50">edit_off</span>
                <p>Select an effect to start editing</p>
            </div>
        `;
    }

    // Hide/gray out timeline
    const timeline = document.getElementById('colorTimeline');
    if (timeline) {
        timeline.style.opacity = '0.2';
        timeline.style.filter = 'grayscale(100%)';
        // Clear the canvas
        const ctx = timeline.getContext('2d');
        ctx.clearRect(0, 0, timeline.width, timeline.height);
        // Draw grayed placeholder
        ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.fillRect(0, 0, timeline.width, timeline.height);
    }

    // Disable action buttons with visual feedback
    const btnSave = document.getElementById('btn-save-effect');
    const btnCancel = document.getElementById('btn-cancel-edit');
    const btnAddStep = document.getElementById('btn-add-step');
    const btnTestEffect = document.getElementById('btn-test-effect');
    const btnStop = document.getElementById('btn-stop-effect');
    const btnRevert = document.getElementById('btn-revert-effect');

    if (btnSave) {
        btnSave.disabled = true;
        btnSave.style.opacity = '0.3';
        btnSave.style.cursor = 'not-allowed';
    }
    if (btnCancel) {
        btnCancel.disabled = true;
        btnCancel.style.opacity = '0.3';
        btnCancel.style.cursor = 'not-allowed';
    }
    if (btnAddStep) {
        btnAddStep.disabled = true;
        btnAddStep.style.opacity = '0.3';
        btnAddStep.style.cursor = 'not-allowed';
    }
    if (btnTestEffect) {
        btnTestEffect.disabled = true;
        btnTestEffect.style.opacity = '0.3';
        btnTestEffect.style.cursor = 'not-allowed';
    }
    if (btnStop) {
        btnStop.disabled = true;
        btnStop.style.opacity = '0.3';
        btnStop.style.cursor = 'not-allowed';
    }
    if (btnRevert) {
        btnRevert.disabled = true;
        btnRevert.style.opacity = '0.3';
        btnRevert.style.cursor = 'not-allowed';
    }
}

// ========================================
// EVENT LISTENERS
// ========================================

function setupEventListeners() {
    // Library category tabs
    document.querySelectorAll('.lib-cat-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            _libCategory = btn.dataset.cat || null;
            _applyLibraryFilter();
            renderEffectsList();
        });
    });

    // Library search input (throttled to avoid excessive re-renders)
    const searchInput = document.getElementById('library-search');
    if (searchInput) {
        const throttledSearch = throttle(value => {
            _libSearchQuery = value;
            _applyLibraryFilter();
            renderEffectsList();
        }, 150);

        searchInput.addEventListener('input', function() {
            throttledSearch(this.value);
        });
    }

    // NEW filter toggle switch
    const toggleFilterNew = document.getElementById('toggle-filter-new');
    if (toggleFilterNew) {
        toggleFilterNew.addEventListener('change', function() {
            filterShowOnlyNew = this.checked;
            _applyLibraryFilter();
            renderEffectsList();
        });
    }

    // New effect button
    const btnNew = document.getElementById('btn-new-effect');
    if (btnNew) {
        btnNew.addEventListener('click', createNewEffect);
    }

    // Add step button
    const btnAddStep = document.getElementById('btn-add-step');
    if (btnAddStep) {
        btnAddStep.addEventListener('click', addStep);
    }

    // Save button
    const btnSave = document.getElementById('btn-save-effect');
    if (btnSave) {
        btnSave.addEventListener('click', saveEffect);
    }

    // Cancel button
    const btnCancel = document.getElementById('btn-cancel-edit');
    if (btnCancel) {
        btnCancel.addEventListener('click', cancelEdit);
    }

    // Test button
    const btnTest = document.getElementById('btn-test-effect');
    if (btnTest) {
        btnTest.addEventListener('click', testCurrentEffect);
    }

    // Stop button
    const btnStop = document.getElementById('btn-stop-effect');
    if (btnStop) {
        btnStop.addEventListener('click', stopEffect);
    }

    // Revert button
    const btnRevert = document.getElementById('btn-revert-effect');
    if (btnRevert) {
        btnRevert.addEventListener('click', revertEffect);
    }
}

// ========================================
// UTILITY
// ========================================

console.log('[Effects] Module loaded');
