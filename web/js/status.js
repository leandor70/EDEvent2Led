'use strict';

// ── Configuration ──────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 750;

// Per-flag metadata: category label, accent color, Material Symbols icon name
const FLAG_META = {
    // ── Ship Flags (Status.json → Flags) — all 32 bits ────────────────────

    // Pericolo immediato
    FSDJump:            { cat: 'Hyperspace', color: 'blue',   icon: 'rocket_launch'         },
    Overheating:        { cat: 'Danger',     color: 'red',    icon: 'thermostat'            },
    BeingInterdicted:   { cat: 'Danger',     color: 'red',    icon: 'warning'               },
    InDanger:           { cat: 'Danger',     color: 'red',    icon: 'emergency'             },
    LowFuel:            { cat: 'Warning',    color: 'amber',  icon: 'local_gas_station'     },

    // FSD state machine
    FsdCharging:        { cat: 'Travel',     color: 'blue',   icon: 'electric_bolt'         },
    MassLocked:         { cat: 'Navigation', color: 'slate',  icon: 'lock'                  },
    FsdCooldown:        { cat: 'Travel',     color: 'cyan',   icon: 'device_thermostat'     },

    // Combattimento
    HardpointsDeployed: { cat: 'Combat',     color: 'orange', icon: 'my_location'           },

    // Stato speciale
    SilentRunning:      { cat: 'Stealth',    color: 'indigo', icon: 'visibility_off'        },
    ScoopingFuel:       { cat: 'Utility',    color: 'yellow', icon: 'local_fire_department' },
    CargoScoopDeployed: { cat: 'Ship',       color: 'amber',  icon: 'storage'               },
    FlightAssistOff:    { cat: 'Flight',     color: 'amber',  icon: 'tune'                  },

    // Navigazione / assetto
    Supercruise:        { cat: 'Travel',     color: 'sky',    icon: 'speed'                 },
    Docked:             { cat: 'Station',    color: 'green',  icon: 'dock'                  },
    Landed:             { cat: 'Planet',     color: 'green',  icon: 'terrain'               },
    LandingGearDown:    { cat: 'Ship',       color: 'slate',  icon: 'flight_land'           },

    // Stato nave
    ShieldsUp:          { cat: 'Defense',    color: 'cyan',   icon: 'shield'                },
    InWing:             { cat: 'Social',     color: 'green',  icon: 'group'                 },
    LightsOn:           { cat: 'Ship',       color: 'yellow', icon: 'light_mode'            },
    NightVision:        { cat: 'Utility',    color: 'violet', icon: 'dark_mode'             },
    HudAnalysisMode:    { cat: 'HUD',        color: 'indigo', icon: 'analytics'             },

    // Veicolo attivo — mutuamente esclusivi
    InMainShip:         { cat: 'Vehicle',    color: 'blue',   icon: 'rocket'                },
    InFighter:          { cat: 'Vehicle',    color: 'sky',    icon: 'flight'                },
    InSRV:              { cat: 'Vehicle',    color: 'yellow', icon: 'electric_car'          },

    // SRV-specific
    SrvHandBrake:       { cat: 'SRV',        color: 'amber',  icon: 'front_hand'            },
    SrvTurretView:      { cat: 'SRV',        color: 'orange', icon: 'center_focus_strong'   },
    SrvTurretRetracted: { cat: 'SRV',        color: 'slate',  icon: 'compress'              },
    SrvDriveAssist:     { cat: 'SRV',        color: 'blue',   icon: 'navigation'            },
    SrvHighBeam:        { cat: 'SRV',        color: 'yellow', icon: 'flashlight_on'         },

    // Informazionali
    HasLatLong:         { cat: 'Nav',        color: 'slate',  icon: 'location_on'           },
    AltFromAvgRadius:   { cat: 'Nav',        color: 'slate',  icon: 'altitude'              },

    // ── Odyssey Flags (Status.json → Flags2) — all 16 bits ────────────────

    // Pericolo critico
    LowOxygen:          { cat: 'Critical',   color: 'red',    icon: 'air'                   },
    LowHealth:          { cat: 'Critical',   color: 'red',    icon: 'favorite'              },
    VeryHot:            { cat: 'Hazard',     color: 'orange', icon: 'local_fire_department' },
    VeryCold:           { cat: 'Hazard',     color: 'cyan',   icon: 'ac_unit'               },

    // Pericoli ambientali
    Hot:                { cat: 'Hazard',     color: 'amber',  icon: 'thermostat'            },
    Cold:               { cat: 'Hazard',     color: 'cyan',   icon: 'thermostat'            },

    // Combattimento
    AimDownSight:       { cat: 'Combat',     color: 'orange', icon: 'gps_fixed'             },

    // Viaggio
    GlideMode:          { cat: 'Travel',     color: 'sky',    icon: 'paragliding'           },

    // Posizione on-foot
    OnFootExterior:     { cat: 'Odyssey',    color: 'green',  icon: 'landscape'             },
    OnFootOnPlanet:     { cat: 'Odyssey',    color: 'green',  icon: 'travel_explore'        },
    OnFootInStation:    { cat: 'Odyssey',    color: 'sky',    icon: 'apartment'             },
    OnFootInHangar:     { cat: 'Odyssey',    color: 'slate',  icon: 'warehouse'             },
    OnFootSocialSpace:  { cat: 'Odyssey',    color: 'purple', icon: 'people'               },

    // Modalità / multiplayer
    OnFoot:             { cat: 'Odyssey',    color: 'purple', icon: 'directions_walk'       },
    InTaxi:             { cat: 'Odyssey',    color: 'sky',    icon: 'local_taxi'            },
    InMulticrew:        { cat: 'Social',     color: 'green',  icon: 'groups'                },
};

// Color tokens — badge, bar, dot/text classes + two-state border+glow
// for the @keyframes flag-border-pulse animation (CSS vars per element).
const CLR = {
    red:    { badge: 'bg-red-500/20 text-red-400',       bar: 'bg-red-500',    dot: 'bg-red-400',    txt: 'text-red-400',    borderDim: 'rgba(239,68,68,.40)', borderBright: 'rgba(239,68,68,.90)', glowDim: '0 0 10px rgba(239,68,68,.10),inset 0 0 10px rgba(239,68,68,.04)', glowBright: '0 0 28px rgba(239,68,68,.38),inset 0 0 18px rgba(239,68,68,.09)'  },
    amber:  { badge: 'bg-amber-500/20 text-amber-400',   bar: 'bg-amber-500',  dot: 'bg-amber-400',  txt: 'text-amber-400',  borderDim: 'rgba(245,158,11,.40)', borderBright: 'rgba(245,158,11,.90)', glowDim: '0 0 10px rgba(245,158,11,.10),inset 0 0 10px rgba(245,158,11,.04)', glowBright: '0 0 28px rgba(245,158,11,.38),inset 0 0 18px rgba(245,158,11,.09)' },
    orange: { badge: 'bg-orange-500/20 text-orange-400', bar: 'bg-orange-500', dot: 'bg-orange-400', txt: 'text-orange-400', borderDim: 'rgba(249,115,22,.40)', borderBright: 'rgba(249,115,22,.90)', glowDim: '0 0 10px rgba(249,115,22,.10),inset 0 0 10px rgba(249,115,22,.04)', glowBright: '0 0 28px rgba(249,115,22,.38),inset 0 0 18px rgba(249,115,22,.09)' },
    blue:   { badge: 'bg-blue-500/20 text-blue-400',     bar: 'bg-blue-500',   dot: 'bg-blue-400',   txt: 'text-blue-400',   borderDim: 'rgba(59,130,246,.40)', borderBright: 'rgba(59,130,246,.90)', glowDim: '0 0 10px rgba(59,130,246,.10),inset 0 0 10px rgba(59,130,246,.04)', glowBright: '0 0 28px rgba(59,130,246,.38),inset 0 0 18px rgba(59,130,246,.09)'  },
    green:  { badge: 'bg-green-500/20 text-green-400',   bar: 'bg-green-500',  dot: 'bg-green-400',  txt: 'text-green-400',  borderDim: 'rgba(34,197,94,.40)', borderBright: 'rgba(34,197,94,.90)', glowDim: '0 0 10px rgba(34,197,94,.10),inset 0 0 10px rgba(34,197,94,.04)', glowBright: '0 0 28px rgba(34,197,94,.38),inset 0 0 18px rgba(34,197,94,.09)'   },
    cyan:   { badge: 'bg-cyan-500/20 text-cyan-400',     bar: 'bg-cyan-500',   dot: 'bg-cyan-400',   txt: 'text-cyan-400',   borderDim: 'rgba(6,182,212,.40)', borderBright: 'rgba(6,182,212,.90)', glowDim: '0 0 10px rgba(6,182,212,.10),inset 0 0 10px rgba(6,182,212,.04)', glowBright: '0 0 28px rgba(6,182,212,.38),inset 0 0 18px rgba(6,182,212,.09)'   },
    sky:    { badge: 'bg-sky-500/20 text-sky-400',       bar: 'bg-sky-500',    dot: 'bg-sky-400',    txt: 'text-sky-400',    borderDim: 'rgba(14,165,233,.40)', borderBright: 'rgba(14,165,233,.90)', glowDim: '0 0 10px rgba(14,165,233,.10),inset 0 0 10px rgba(14,165,233,.04)', glowBright: '0 0 28px rgba(14,165,233,.38),inset 0 0 18px rgba(14,165,233,.09)'  },
    indigo: { badge: 'bg-indigo-500/20 text-indigo-400', bar: 'bg-indigo-500', dot: 'bg-indigo-400', txt: 'text-indigo-400', borderDim: 'rgba(99,102,241,.40)', borderBright: 'rgba(99,102,241,.90)', glowDim: '0 0 10px rgba(99,102,241,.10),inset 0 0 10px rgba(99,102,241,.04)', glowBright: '0 0 28px rgba(99,102,241,.38),inset 0 0 18px rgba(99,102,241,.09)'  },
    yellow: { badge: 'bg-yellow-500/20 text-yellow-400', bar: 'bg-yellow-500', dot: 'bg-yellow-400', txt: 'text-yellow-400', borderDim: 'rgba(234,179,8,.40)', borderBright: 'rgba(234,179,8,.90)', glowDim: '0 0 10px rgba(234,179,8,.10),inset 0 0 10px rgba(234,179,8,.04)', glowBright: '0 0 28px rgba(234,179,8,.38),inset 0 0 18px rgba(234,179,8,.09)'    },
    violet: { badge: 'bg-violet-500/20 text-violet-400', bar: 'bg-violet-500', dot: 'bg-violet-400', txt: 'text-violet-400', borderDim: 'rgba(139,92,246,.40)', borderBright: 'rgba(139,92,246,.90)', glowDim: '0 0 10px rgba(139,92,246,.10),inset 0 0 10px rgba(139,92,246,.04)', glowBright: '0 0 28px rgba(139,92,246,.38),inset 0 0 18px rgba(139,92,246,.09)'  },
    purple: { badge: 'bg-purple-500/20 text-purple-400', bar: 'bg-purple-500', dot: 'bg-purple-400', txt: 'text-purple-400', borderDim: 'rgba(168,85,247,.40)', borderBright: 'rgba(168,85,247,.90)', glowDim: '0 0 10px rgba(168,85,247,.10),inset 0 0 10px rgba(168,85,247,.04)', glowBright: '0 0 28px rgba(168,85,247,.38),inset 0 0 18px rgba(168,85,247,.09)'  },
    slate:  { badge: 'bg-slate-500/20 text-slate-400',   bar: 'bg-slate-500',  dot: 'bg-slate-400',  txt: 'text-slate-400',  borderDim: 'rgba(100,116,139,.40)', borderBright: 'rgba(100,116,139,.90)', glowDim: '0 0 10px rgba(100,116,139,.10),inset 0 0 10px rgba(100,116,139,.04)', glowBright: '0 0 28px rgba(100,116,139,.38),inset 0 0 18px rgba(100,116,139,.09)' },
};

// ── State ───────────────────────────────────────────────────────────────────

let _pollTimer   = null;
let _cardsBuilt  = false;
// Filter state
let _filterSection  = 'all';
let _filterPriority = 0;
// Current flag data (name → flag object)
let _flagsById   = {};
// Inline step editor modules
let _moduleOn    = null;
let _moduleOff   = null;
// Modal state
let _currentFlagName  = null;
let _currentOnEffect  = null;
let _currentOffEffect = null;
let _activeStatusSlot = 'on';   // which tab is visible
// Template cache
let _statusTemplates = [];

// ── Boot ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // Init both editor modules — timelineCanvasId:null delegates to page-level renderColorTimeline()
    _moduleOn = new EffectEditorModule({
        stepsContainerId: 'status-steps-on',
        timelineCanvasId: null,
        onStepsChange: (steps) => {
            if (_currentOnEffect && typeof _currentOnEffect === 'object') _currentOnEffect.steps = steps;
            _updateStatusTabBadge('on', steps);
        },
    });
    _moduleOff = new EffectEditorModule({
        stepsContainerId: 'status-steps-off',
        timelineCanvasId: null,
        onStepsChange: (steps) => {
            if (_currentOffEffect && typeof _currentOffEffect === 'object') _currentOffEffect.steps = steps;
            _updateStatusTabBadge('off', steps);
        },
    });
    await Promise.all([_moduleOn.init(), _moduleOff.init()]);

    if (typeof eel !== 'undefined') {
        eel.cancel_shutdown()();
        loadStatus();
        _pollTimer = setInterval(loadStatus, POLL_INTERVAL_MS);
    } else {
        renderOffline();
    }
    _wireModal();
    _wireFilters();
    requestAnimationFrame(() => document.body.classList.add('loaded'));
});

// ── Performance: Stop polling when window loses focus ────────────────────────
window.addEventListener('app-window-blurred', () => {
    if (_pollTimer) {
        clearInterval(_pollTimer);
        _pollTimer = null;
        console.log('[Status] Polling stopped (window blurred)');
    }
});

window.addEventListener('app-window-focused', () => {
    if (!_pollTimer && typeof eel !== 'undefined') {
        loadStatus();  // Immediate poll on focus restore
        _pollTimer = setInterval(loadStatus, POLL_INTERVAL_MS);
        console.log('[Status] Polling resumed (window focused)');
    }
});

// ── Cleanup: Stop polling when page unloads ──────────────────────────────────
window.addEventListener('beforeunload', () => {
    if (_pollTimer) {
        clearInterval(_pollTimer);
        _pollTimer = null;
        console.log('[Status] Polling cleared (page unload)');
    }
});

// ── Poll ─────────────────────────────────────────────────────────────────────

async function loadStatus() {
    try {
        const data = await eel.get_game_status()();
        if (!data) return;

        // Keep flag map in sync for the assignment modal
        [...(data.ship_flags || []), ...(data.odyssey_flags || [])].forEach(f => {
            _flagsById[f.name] = f;
        });

        if (!_cardsBuilt) {
            buildGrid('ship-flags-grid',    data.ship_flags);
            buildGrid('odyssey-flags-grid', data.odyssey_flags);
            _cardsBuilt = true;
        }

        updateAllCards(data);
        updateStatsBar(data);
        _applyFilters();

        const el = document.getElementById('stat-last-update');
        if (el) el.textContent = new Date().toLocaleTimeString();

    } catch (e) {
        console.error('[status.js] poll error:', e);
    }
}

// ── Card grid construction ────────────────────────────────────────────────────

function buildGrid(containerId, flags) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    if (!flags || flags.length === 0) {
        container.innerHTML = `<div class="col-span-4 py-8 text-center text-white/30 text-sm italic">${window.i18n.get('status_strings.no_flags_defined') || 'No flags defined'}</div>`;
        return;
    }
    flags.forEach(flag => container.appendChild(makeCard(flag)));
}

function makeCard(flag) {
    const { name, priority } = flag;
    const meta = FLAG_META[name] || { cat: 'Unknown', color: 'slate', icon: 'help' };
    const c    = CLR[meta.color]  || CLR.slate;

    // 10 mini priority bars
    const bars = Array.from({ length: 10 }, (_, i) =>
        `<div class="w-1 h-2.5 rounded-sm ${i < priority ? c.bar : 'bg-white/10'}"></div>`
    ).join('');

    const div = document.createElement('div');
    div.id                  = `flag-${name}`;
    div.className           = 'sci-fi-border carbon-pattern p-3 transition-all duration-300 cursor-pointer group';
    div.title               = 'Click to assign effects';
    div.dataset.priority    = priority;
    div.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <span class="text-xs px-1.5 py-0.5 rounded uppercase tracking-wider leading-tight ${c.badge}">${meta.cat}</span>
            <div class="flex gap-0.5 items-end">${bars}</div>
        </div>
        <div class="flag-name orbitron text-sm tracking-wider mb-1.5 text-white/50 leading-tight">${splitCamel(name)}</div>
        <div class="flag-effects mb-1.5 flex gap-1.5 items-center min-w-0 empty:hidden"></div>
        <div class="flex items-center gap-2">
            <div class="flag-dot w-2 h-2 rounded-full flex-shrink-0 bg-white/20"></div>
            <span class="flag-status text-[11px] uppercase tracking-widest text-white/30">inactive</span>
        </div>`;

    div.addEventListener('click', () => openStatusAssign(name));
    return div;
}

// "BeingInterdicted" → "Being Interdicted"
function splitCamel(name) {
    return name.replace(/([A-Z])/g, ' $1').trim();
}

// ── Card state update ─────────────────────────────────────────────────────────

function updateAllCards(data) {
    let shipActive = 0, odysseyActive = 0;

    (data.ship_flags    || []).forEach(f => { applyCardState(f); if (f.active) shipActive++; });
    (data.odyssey_flags || []).forEach(f => { applyCardState(f); if (f.active) odysseyActive++; });

    const sc = document.getElementById('ship-active-count');
    // get(key, vars) translates AND fills {{count}}; interpolate() expects a text, not a key
    if (sc) sc.textContent = i18n.get('status_page.active_count', { count: shipActive });

    const oc = document.getElementById('odyssey-active-count');
    if (oc) oc.textContent = i18n.get('status_page.active_count', { count: odysseyActive });
}

function applyCardState(flag) {
    const card = document.getElementById(`flag-${flag.name}`);
    if (!card) return;

    const meta = FLAG_META[flag.name] || { color: 'slate' };
    const c    = CLR[meta.color] || CLR.slate;

    const dot   = card.querySelector('.flag-dot');
    const label = card.querySelector('.flag-status');
    const title = card.querySelector('.flag-name');

    if (flag.active) {
        // Set CSS vars used by @keyframes flag-border-pulse
        card.style.setProperty('--border-dim',    c.borderDim);
        card.style.setProperty('--border-bright',  c.borderBright);
        card.style.setProperty('--glow-dim',       c.glowDim);
        card.style.setProperty('--glow-bright',    c.glowBright);
        card.classList.add('flag-card-active');
        // Clear any residual inline border/shadow (animation owns them now)
        card.style.borderColor = '';
        card.style.boxShadow   = '';
        dot.className   = `flag-dot w-2 h-2 rounded-full flex-shrink-0 animate-pulse ${c.dot}`;
        label.textContent = window.i18n.get('status_strings.flag_active') || 'ACTIVE';
        label.className   = `flag-status text-xs font-bold uppercase tracking-widest ${c.txt}`;
        title.className   = 'flag-name orbitron text-sm tracking-wider mb-0.5 text-white leading-tight';
    } else {
        card.classList.remove('flag-card-active');
        card.style.borderColor = '';
        card.style.boxShadow   = '';
        dot.className   = 'flag-dot w-2 h-2 rounded-full flex-shrink-0 bg-white/20';
        label.textContent = window.i18n.get('status_strings.flag_inactive') || 'inactive';
        label.className   = 'flag-status text-xs uppercase tracking-widest text-white/50';
        title.className   = 'flag-name orbitron text-sm tracking-wider mb-0.5 text-white/65 leading-tight';
    }

    // Sync effects row: show ON / OFF effect names from inline data
    const effectsRow = card.querySelector('.flag-effects');
    if (effectsRow) {
        effectsRow.innerHTML = '';
        const onName  = flag.on_effect_name  || null;
        const offName = flag.off_effect_name || null;

        if (onName) {
            const pill = document.createElement('span');
            pill.className = 'inline-flex items-center gap-0.5 text-[10px] leading-none px-1 py-0.5 rounded '
                           + 'bg-green-500/15 text-green-400/85 max-w-[100px] truncate flex-shrink min-w-0';
            pill.title = `ON effect: ${onName}`;
            pill.textContent = '\u25b2\u00a0' + onName;  // ▲ name
            effectsRow.appendChild(pill);
        }
        if (offName) {
            const pill = document.createElement('span');
            pill.className = 'inline-flex items-center gap-0.5 text-[10px] leading-none px-1 py-0.5 rounded '
                           + 'bg-red-500/15 text-red-400/75 max-w-[100px] truncate flex-shrink min-w-0';
            pill.title = `OFF effect: ${offName}`;
            pill.textContent = '\u25bc\u00a0' + offName;  // ▼ name
            effectsRow.appendChild(pill);
        }
    }
}


// ── Filters ───────────────────────────────────────────────────────────────────

function _wireFilters() {
    // Section buttons — same category-filter pattern as Events
    document.querySelectorAll('.status-section-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            _filterSection = btn.dataset.section;
            document.querySelectorAll('.status-section-btn')
                .forEach(b => b.classList.toggle('active', b === btn));
            _applyFilters();
        });
    });

    // Priority slider — same pattern as Events importance filter
    const slider = document.getElementById('status-priority-filter');
    const label  = document.getElementById('status-priority-label');
    if (slider) {
        slider.addEventListener('input', () => {
            _filterPriority = parseInt(slider.value, 10);
            if (label) label.textContent = _filterPriority === 0 ? (window.i18n.get('status_strings.all_filter') || 'All') : _filterPriority;
            _applyFilters();
        });
    }
}

/**
 * Show/hide sections and cards based on current filter state.
 * Called after every poll update and on every filter button click.
 */
function _applyFilters() {
    // Section visibility
    const shipSec    = document.getElementById('section-ship');
    const odysseySec = document.getElementById('section-odyssey');
    if (shipSec)    shipSec.style.display    = _filterSection === 'odyssey' ? 'none' : '';
    if (odysseySec) odysseySec.style.display = _filterSection === 'ship'    ? 'none' : '';

    // Card visibility based on priority
    document.querySelectorAll('#ship-flags-grid .sci-fi-border, #odyssey-flags-grid .sci-fi-border')
        .forEach(card => {
            const prio = parseInt(card.dataset.priority, 10) || 0;
            card.style.display = prio >= _filterPriority ? '' : 'none';
        });
}

// ── Tab switching ─────────────────────────────────────────────────────────────

function switchStatusTab(slot) {
    _activeStatusSlot = slot;

    const onBtn   = document.getElementById('tab-btn-on');
    const offBtn  = document.getElementById('tab-btn-off');
    const onGlow  = document.getElementById('tab-glow-on');
    const offGlow = document.getElementById('tab-glow-off');
    const onInner = document.getElementById('tab-inner-on');
    const offInner= document.getElementById('tab-inner-off');
    const onEd    = document.getElementById('status-editor-on');
    const offEd   = document.getElementById('status-editor-off');

    if (slot === 'on') {
        onBtn.style.opacity  = '1';
        offBtn.style.opacity = '0.38';
        if (onGlow)  onGlow.style.opacity  = '0.6';
        if (offGlow) offGlow.style.opacity = '0';
        if (onInner)  { onInner.style.borderColor  = 'rgba(34,197,94,0.75)';  onInner.style.background  = 'rgba(34,197,94,0.09)'; }
        if (offInner) { offInner.style.borderColor = 'rgba(239,68,68,0.25)';  offInner.style.background = 'rgba(239,68,68,0.03)'; }
        onEd?.classList.remove('hidden');
        offEd?.classList.add('hidden');
    } else {
        offBtn.style.opacity = '1';
        onBtn.style.opacity  = '0.38';
        if (offGlow) offGlow.style.opacity = '0.6';
        if (onGlow)  onGlow.style.opacity  = '0';
        if (offInner) { offInner.style.borderColor = 'rgba(239,68,68,0.75)';  offInner.style.background = 'rgba(239,68,68,0.09)'; }
        if (onInner)  { onInner.style.borderColor  = 'rgba(34,197,94,0.25)';  onInner.style.background  = 'rgba(34,197,94,0.03)'; }
        offEd?.classList.remove('hidden');
        onEd?.classList.add('hidden');
    }
}

function _updateStatusTabBadge(slot, steps) {
    const count = Array.isArray(steps) ? steps.length : 0;
    const el = document.getElementById(slot === 'on' ? 'tab-on-badge' : 'tab-off-badge');
    if (!el) return;
    el.textContent = count > 0 ? count + ' step' + (count !== 1 ? 's' : '') : 'none';
}

async function stopStatusEffect() {
    await api('stop_current_effect');
}

// ── Color Timeline (rich renderer — same visual as effects-editor / events) ───

function renderColorTimeline() {
    _renderStatusTimeline('on');
    _renderStatusTimeline('off');
}

function _renderStatusTimeline(slot) {
    const canvasId    = 'status-colorTimeline-' + slot;
    const containerId = 'status-steps-' + slot;
    const totalId     = 'status-totalDuration-' + slot;
    const endId       = 'status-endTime-' + slot;

    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx   = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const steps = [];
    document.querySelectorAll('#' + containerId + ' .step-card').forEach((card, idx) => {
        const durInput  = card.querySelector('.step-duration');
        const colorInps = card.querySelectorAll('.step-color');
        const typeSelect= card.querySelector('.step-type');
        if (!durInput || colorInps.length === 0) return;
        const colors = Array.from(colorInps).map(i => (i.value && i.value.startsWith('#')) ? i.value : '#0055FF');
        const numLoopsInp = card.querySelector('.param-num-loops');
        steps.push({
            duration:   parseInt(durInput.value) || 500,
            colors,
            effectType: typeSelect ? typeSelect.value : 'static_transition',
            numLoops:   numLoopsInp ? parseInt(numLoopsInp.value) || 1 : 1,
            name:       typeSelect?.options[typeSelect.selectedIndex]?.text || 'Effect',
            index:      idx + 1,
        });
    });

    const fmt = ms => ms >= 1000 ? (ms / 1000).toFixed(1) + 's' : ms + 'ms';
    const totalDuration = steps.reduce((s, st) => s + st.duration, 0);
    const totalEl = document.getElementById(totalId);
    const endEl   = document.getElementById(endId);
    if (totalEl) totalEl.textContent = (window.i18n.get('status_strings.total_prefix') || 'Total: ') + fmt(totalDuration);
    if (endEl)   endEl.textContent   = fmt(totalDuration);
    if (steps.length === 0) return;

    const pad = 20, tH = 60, tY = 20, lblY = tY + tH + 15;
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.fillRect(pad, tY, width - pad * 2, tH);

    // Draw segments
    let x = pad;
    steps.forEach((st, i) => {
        const sw = ((width - pad * 2) * st.duration) / totalDuration;
        const prev = i > 0 ? steps[i - 1].colors[0] : '#000000';
        switch (st.effectType) {
            case 'breath':
                if (st.colors.length >= 2) {
                    const loops = st.numLoops, cw = sw / loops;
                    for (let n = 0; n < loops; n++) {
                        const cx = x + n * cw, half = cw / 2;
                        const g1 = ctx.createLinearGradient(cx, 0, cx + half, 0);
                        g1.addColorStop(0, st.colors[0]); g1.addColorStop(1, st.colors[1]);
                        ctx.fillStyle = g1; ctx.fillRect(cx, tY, half, tH);
                        const g2 = ctx.createLinearGradient(cx + half, 0, cx + cw, 0);
                        g2.addColorStop(0, st.colors[1]); g2.addColorStop(1, st.colors[0]);
                        ctx.fillStyle = g2; ctx.fillRect(cx + half, tY, half, tH);
                    }
                } else { ctx.fillStyle = st.colors[0]; ctx.fillRect(x, tY, sw, tH); }
                break;
            case 'color_cycle':
                if (st.colors.length >= 2) {
                    const bw = sw / st.colors.length;
                    st.colors.forEach((c, ci) => {
                        const g = ctx.createLinearGradient(x + ci * bw, 0, x + (ci + 1) * bw, 0);
                        g.addColorStop(0, c); g.addColorStop(0.7, c); g.addColorStop(1, st.colors[(ci + 1) % st.colors.length]);
                        ctx.fillStyle = g; ctx.fillRect(x + ci * bw, tY, bw, tH);
                    });
                } else { ctx.fillStyle = st.colors[0]; ctx.fillRect(x, tY, sw, tH); }
                break;
            case 'static_transition': {
                const g = ctx.createLinearGradient(x, tY, x + sw, tY);
                g.addColorStop(0, prev); g.addColorStop(1, st.colors[0]);
                ctx.fillStyle = g; ctx.fillRect(x, tY, sw, tH);
                break;
            }
            default:
                if (st.colors.length >= 2) {
                    const bh = tH / st.colors.length;
                    st.colors.forEach((c, ci) => { ctx.fillStyle = c; ctx.fillRect(x, tY + ci * bh, sw, bh); });
                } else { ctx.fillStyle = st.colors[0]; ctx.fillRect(x, tY, sw, tH); }
                break;
        }
        // Step label
        ctx.font = '10px Orbitron, monospace'; ctx.textAlign = 'center';
        const lx = x + sw / 2;
        ctx.fillStyle = '#FF6600'; ctx.fillText('Step ' + st.index, lx, lblY);
        ctx.fillStyle = 'rgba(255,255,255,0.6)'; ctx.font = '9px Rajdhani, sans-serif';
        ctx.fillText(fmt(st.duration), lx, lblY + 12);
        x += sw;
    });

    // Step boundary markers
    x = pad; let cum = 0;
    steps.forEach((st, i) => {
        const sw = ((width - pad * 2) * st.duration) / totalDuration;
        if (i > 0) {
            ctx.strokeStyle = 'rgba(255,102,0,0.5)'; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
            ctx.beginPath(); ctx.moveTo(x, tY); ctx.lineTo(x, tY + tH); ctx.stroke(); ctx.setLineDash([]);
            ctx.fillStyle = '#FF6600'; ctx.font = 'bold 9px Rajdhani, sans-serif'; ctx.textAlign = 'center';
            ctx.fillText(fmt(cum), x, tY - 5);
        }
        x += sw; cum += st.duration;
    });

    // Intermediate ticks
    const tw = width - pad * 2;
    const tick = totalDuration <= 2000 ? 250 : totalDuration <= 5000 ? 500 : 1000;
    ctx.strokeStyle = 'rgba(255,255,255,0.4)'; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
    for (let t = tick; t < totalDuration; t += tick) {
        const tx = pad + (tw * t / totalDuration);
        let tooClose = false; let ct = 0;
        for (const s of steps) { ct += s.duration; if (Math.abs(tx - (pad + tw * ct / totalDuration)) < 15) { tooClose = true; break; } }
        if (!tooClose) {
            ctx.beginPath(); ctx.moveTo(tx, tY + tH * 0.2); ctx.lineTo(tx, tY + tH * 0.8); ctx.stroke();
            if (t % 1000 === 0) { ctx.fillStyle = 'rgba(255,255,255,0.3)'; ctx.font = '8px Rajdhani, sans-serif'; ctx.textAlign = 'center'; ctx.fillText((t / 1000).toFixed(1) + 's', tx, tY + tH + 8); }
        }
    }
    ctx.setLineDash([]);

    // Outer border + sci-fi corners
    ctx.strokeStyle = 'rgba(255,102,0,0.3)'; ctx.lineWidth = 1;
    ctx.strokeRect(pad, tY, width - pad * 2, tH);
    const cs = 8; ctx.strokeStyle = '#FF6600'; ctx.lineWidth = 2;
    [[pad, tY+cs, pad, tY, pad+cs, tY], [width-pad-cs, tY, width-pad, tY, width-pad, tY+cs],
     [pad, tY+tH-cs, pad, tY+tH, pad+cs, tY+tH], [width-pad-cs, tY+tH, width-pad, tY+tH, width-pad, tY+tH-cs]
    ].forEach(([x1,y1,x2,y2,x3,y3]) => { ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.lineTo(x3,y3); ctx.stroke(); });
}

// ── Status effect assignment modal ────────────────────────────────────────────

function _wireModal() {
    const modal     = document.getElementById('status-assign-modal');
    const backdrop  = document.getElementById('status-modal-backdrop');
    const btnClose  = document.getElementById('status-modal-close');
    const btnCancel = document.getElementById('status-modal-cancel');
    const btnSave   = document.getElementById('status-modal-save');
    const btnClear  = document.getElementById('status-modal-clear');

    if (!modal) return;

    const close = () => { modal.classList.add('hidden'); _currentFlagName = null; };
    backdrop?.addEventListener('click', close);
    btnClose?.addEventListener('click',  close);
    btnCancel?.addEventListener('click', close);

    btnSave?.addEventListener('click', async () => {
        if (!_currentFlagName) return;

        let onEffect  = _currentOnEffect;
        let offEffect = _currentOffEffect;

        if (typeof onEffect === 'object' && onEffect !== null && _moduleOn) {
            onEffect = { ...onEffect, steps: _moduleOn.getSteps() };
        }
        if (typeof offEffect === 'object' && offEffect !== null && _moduleOff) {
            offEffect = { ...offEffect, steps: _moduleOff.getSteps() };
        }

        const r = await api('set_status_flag_mapping', _currentFlagName, onEffect, offEffect, true);
        if (r?.success) {
            showNotification(window.i18n.interpolate('notifications.assignment_saved_for', {flag: _currentFlagName}) || `Assignment saved for ${_currentFlagName}`, 'success');
            close();
            _cardsBuilt = false;
        } else {
            showNotification(r?.error || window.i18n.get('notifications.save_failed') || 'Save failed', 'error');
        }
    });

    btnClear?.addEventListener('click', async () => {
        if (!_currentFlagName) return;
        const r = await api('clear_status_flag_mapping', _currentFlagName);
        if (r?.success) {
            showNotification(window.i18n.interpolate('notifications.assignment_cleared_for', {flag: _currentFlagName}) || `Assignment cleared for ${_currentFlagName}`, 'info');
            close();
            _cardsBuilt = false;
        } else {
            showNotification(r?.error || window.i18n.get('notifications.save_failed') || 'Clear failed', 'error');
        }
    });
}

async function openStatusAssign(flagName) {
    const modal = document.getElementById('status-assign-modal');
    if (!modal) return;

    _currentFlagName = flagName;

    const nameEl = document.getElementById('status-modal-flag-name');
    if (nameEl) nameEl.textContent = splitCamel(flagName);

    const flag = _flagsById[flagName] || {};
    _currentOnEffect  = flag.on_effect  ? JSON.parse(JSON.stringify(flag.on_effect))  : null;
    _currentOffEffect = flag.off_effect ? JSON.parse(JSON.stringify(flag.off_effect)) : null;

    if (!_currentOnEffect) _currentOnEffect = _buildStatusEffect(flagName, 'on');

    // Populate effect name inputs
    const nameOn  = document.getElementById('status-effect-name-on');
    const nameOff = document.getElementById('status-effect-name-off');
    if (nameOn)  nameOn.value  = (typeof _currentOnEffect  === 'object' && _currentOnEffect)  ? (_currentOnEffect.name  || '') : '';
    if (nameOff) nameOff.value = (typeof _currentOffEffect === 'object' && _currentOffEffect) ? (_currentOffEffect.name || '') : '';

    // Sync name changes back to effect object
    if (nameOn)  nameOn.oninput  = () => { if (_currentOnEffect  && typeof _currentOnEffect  === 'object') _currentOnEffect.name  = nameOn.value; };
    if (nameOff) nameOff.oninput = () => { if (_currentOffEffect && typeof _currentOffEffect === 'object') _currentOffEffect.name = nameOff.value; };

    if (_moduleOn)  _moduleOn.loadEffect(_currentOnEffect);
    if (_moduleOff) _moduleOff.loadEffect(_currentOffEffect);

    // Update tab badges
    _updateStatusTabBadge('on',  _currentOnEffect?.steps  || []);
    _updateStatusTabBadge('off', _currentOffEffect?.steps || []);

    // Always open on ON tab
    switchStatusTab('on');

    modal.classList.remove('hidden');
}

function _buildStatusEffect(flagName, slot) {
    return {
        name: `${flagName} ${slot.toUpperCase()}`,
        steps: [],
        topology_support: ['1D', '2D'],
        post_behavior: 'static_color',
        post_behavior_data: null,
        category: 'status',
        metadata: {},
    };
}


// ── Per-slot actions (buttons inside the modal) ───────────────────────────────

function addStatusStep(slot) {
    const mod = slot === 'on' ? _moduleOn : _moduleOff;
    if (!mod) return;
    if (slot === 'off' && !_currentOffEffect) {
        _currentOffEffect = _buildStatusEffect(_currentFlagName || 'Status', 'off');
        mod.loadEffect(_currentOffEffect);
    }
    mod.addStep();
}

async function testStatusSlot(slot) {
    const mod    = slot === 'on' ? _moduleOn   : _moduleOff;
    const effect = slot === 'on' ? _currentOnEffect : _currentOffEffect;
    if (!mod || !effect || typeof effect !== 'object') {
        showNotification(window.i18n.get('notifications.no_effect_to_test') || 'No effect to test', 'warning');
        return;
    }
    const effectData = { ...effect, steps: mod.getSteps() };
    showNotification(window.i18n.get('notifications.testing_effect_short') || 'Testing effect...', 'info');
    const r = await api('test_status_effect_live', _currentFlagName, slot, effectData);
    if (!r?.success) showNotification(r?.error || window.i18n.get('notifications.save_failed') || 'Test failed', 'error');
    else showNotification(window.i18n.get('notifications.effect_playing_hardware') || 'Effect playing on hardware', 'success');
}

function setStatusSlotNone(slot) {
    if (slot === 'on') {
        _currentOnEffect = null;
        _moduleOn?.loadEffect(null);
    } else {
        _currentOffEffect = null;
        _moduleOff?.loadEffect(null);
    }
}

async function importStatusTemplate(slot) {
    if (_statusTemplates.length === 0) {
        const r = await api('get_effect_templates');
        _statusTemplates = r?.templates || [];
    }
    _showStatusTemplateModal(slot);
}

function _showStatusTemplateModal(slot) {
    const existing = document.getElementById('_status-template-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = '_status-template-overlay';
    overlay.className = 'fixed inset-0 z-[10002] flex items-center justify-center';
    overlay.innerHTML = `
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" id="_stmpl-bg"></div>
        <div class="relative z-[10003] w-[90%] max-w-[520px] max-h-[70vh] flex flex-col"
             style="background:rgba(5,7,10,0.97);border:1px solid rgba(255,102,0,0.3);border-radius:10px;">
            <div class="flex items-center justify-between px-5 py-3 border-b border-white/10 flex-shrink-0">
                <span class="orbitron text-sm text-white tracking-wider">Template → ${escapeHtml(slot.toUpperCase())}</span>
                <button id="_stmpl-close" class="text-white/40 hover:text-white">
                    <span class="material-symbols-outlined" style="font-size:18px;">close</span>
                </button>
            </div>
            <div class="flex-1 overflow-y-auto p-3 space-y-2">
                ${_statusTemplates.map((t, i) => `
                    <div class="_stmpl-item cursor-pointer p-2 rounded border border-white/8
                                 hover:bg-[rgba(255,102,0,0.08)] hover:border-[rgba(255,102,0,0.3)] transition-colors"
                         data-index="${i}">
                        <div class="text-sm" style="color:rgba(255,255,255,0.8);">${escapeHtml(t._template_name || t.name || 'Unnamed')}</div>
                        <div class="text-xs" style="color:rgba(255,255,255,0.3);">${(t.steps||[]).length} steps</div>
                    </div>`).join('')}
                ${_statusTemplates.length === 0
                    ? '<div class="text-center py-6 text-sm" style="color:rgba(255,255,255,0.3);">No templates available</div>' : ''}
            </div>
        </div>`;

    document.body.appendChild(overlay);
    document.getElementById('_stmpl-bg')?.addEventListener('click',    () => overlay.remove());
    document.getElementById('_stmpl-close')?.addEventListener('click', () => overlay.remove());

    overlay.querySelectorAll('._stmpl-item').forEach(item => {
        item.addEventListener('click', () => {
            const idx  = parseInt(item.dataset.index, 10);
            const tmpl = _statusTemplates[idx];
            if (!tmpl) return;
            const clean = { ...tmpl };
            delete clean._template_id;
            delete clean._template_name;

            if (slot === 'on') {
                _currentOnEffect = JSON.parse(JSON.stringify(clean));
                _moduleOn?.loadEffect(_currentOnEffect);
            } else {
                _currentOffEffect = JSON.parse(JSON.stringify(clean));
                _moduleOff?.loadEffect(_currentOffEffect);
            }
            overlay.remove();
            showNotification(`Template: ${clean.name || 'Unnamed'}`, 'success');
        });
    });
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function updateStatsBar(data) {
    // Monitoring indicator
    const dot = document.getElementById('monitoring-dot');
    const txt = document.getElementById('monitoring-text');
    const sub = document.getElementById('monitoring-sub');
    if (dot && txt) {
        if (data.monitoring) {
            dot.className = 'w-3 h-3 rounded-full bg-green-400 shadow-[0_0_8px_rgba(34,197,94,.8)] animate-pulse';
            txt.textContent = window.i18n.get('status_strings.monitoring_active') || 'Active';
            txt.className   = 'orbitron text-sm tracking-wider font-bold text-green-400';
            if (sub) sub.textContent = window.i18n.get('status_strings.status_monitored') || 'Status.json monitored';
        } else {
            dot.className = 'w-3 h-3 rounded-full bg-white/20';
            txt.textContent = window.i18n.get('status_strings.monitoring_inactive') || 'Inactive';
            txt.className   = 'orbitron text-sm tracking-wider text-white/40';
            if (sub) sub.textContent = window.i18n.get('status_strings.start_monitoring_hint') || 'Start monitoring to activate';
        }
    }

    // Total active alerts
    const total = [...(data.ship_flags || []), ...(data.odyssey_flags || [])].filter(f => f.active).length;
    const alertEl = document.getElementById('stat-active-count');
    if (alertEl) {
        alertEl.textContent = total;
        alertEl.className   = total > 0
            ? 'text-4xl font-bold orbitron text-[var(--primary-accent)] tabular-nums'
            : 'text-4xl font-bold orbitron text-white/20 tabular-nums';
    }

    // Raw hex values
    const flagsEl  = document.getElementById('stat-flags-hex');
    const flags2El = document.getElementById('stat-flags2-hex');
    if (flagsEl)  flagsEl.textContent  = '0x' + (data.flags  || 0).toString(16).toUpperCase().padStart(8, '0');
    if (flags2El) flags2El.textContent = '0x' + (data.flags2 || 0).toString(16).toUpperCase().padStart(8, '0');
}

// ── Offline (no Eel) ──────────────────────────────────────────────────────────

function renderOffline() {
    ['ship-flags-grid', 'odyssey-flags-grid'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = `<div class="col-span-4 py-12 text-center text-white/30 text-sm italic">${window.i18n.get('status_strings.connect_to_see_status') || 'Connect to the application to see live game status'}</div>`;
    });
    requestAnimationFrame(() => document.body.classList.add('loaded'));
}
