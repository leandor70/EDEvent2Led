/**
 * Activity Logs — real-time log viewer for ED:Event2Led.
 *
 * Architecture:
 *   Python side: deque(maxlen=2000) in log_buffer.py (auto-drops oldest)
 *   JS side:     allEntries array (capped at 2000 client-side) + DOM cap at 500 visible rows
 *
 * Real-time: Python calls eel.receive_log(entry) → JS appends incrementally (O(1)).
 * Initial load: get_logs() returns full buffer snapshot on page open.
 */

// ── Constants ────────────────────────────────────────────────────────────────

const DOM_CAP = 500;      // Max rows rendered in the DOM at once
const MEM_CAP = 2000;     // Max entries kept in JS memory (mirrors Python deque)

// Maps category string → CSS class for colour
const CATEGORY_CSS = {
    EVENT:   'log-event',
    RENDER:  'log-render',
    OPENRGB: 'log-openrgb',
    SYSTEM:  'log-openrgb',
    WARNING: 'log-warning',
    ERROR:   'log-error',
};

// Maps category → filter group (used by filter buttons)
const CATEGORY_FILTER = {
    EVENT:   'event',
    RENDER:  'render',
    OPENRGB: 'openrgb',
    SYSTEM:  'openrgb',
    WARNING: 'error',
    ERROR:   'error',
};

// CSS classes for active / inactive filter buttons
const BTN_ACTIVE   = 'px-3 py-2 text-[13px] uppercase tracking-wider bg-[var(--primary-accent)] text-white rounded';
const BTN_INACTIVE = 'px-3 py-2 text-[13px] uppercase tracking-wider border border-white/20 text-white/60 rounded hover:bg-white/5';

// All possible filter values (used to check if "All" should appear active)
const ALL_FILTER_VALUES = new Set(['event', 'render', 'openrgb', 'error']);

// ── State ────────────────────────────────────────────────────────────────────

let allEntries    = [];                          // Full in-memory list of log entries (newest last)
let activeFilters = new Set(ALL_FILTER_VALUES);  // Set of active filter groups (all enabled by default)
let searchText    = '';                          // Lowercase search string (empty = no filter)
let autoScroll    = true;                        // Whether to auto-scroll to bottom on new entries

// ── Helpers ──────────────────────────────────────────────────────────────────
// NOTE: escapeHtml() is defined in common.js (imported globally)

function formatEntry(entry) {
    const css = CATEGORY_CSS[entry.category] || '';
    return `<div class="log-entry">` +
        `<span class="log-timestamp">[${entry.ts}]</span> ` +
        `<span class="log-category ${css}">[${entry.category}]</span> ` +
        escapeHtml(entry.message) +
        `</div>`;
}

function matchesFilter(entry) {
    const group = CATEGORY_FILTER[entry.category] || 'openrgb';
    if (!activeFilters.has(group)) return false;
    if (searchText) {
        const haystack = (entry.category + ' ' + entry.message).toLowerCase();
        if (!haystack.includes(searchText)) return false;
    }
    return true;
}

function getViewer() {
    return document.getElementById('log-viewer');
}

// ── Rendering ────────────────────────────────────────────────────────────────

/**
 * Full re-render of the log viewer from allEntries.
 * Used after filter/search changes. Shows last DOM_CAP matching entries.
 */
function renderLog() {
    const viewer = getViewer();
    if (!viewer) return;

    const filtered = allEntries.filter(matchesFilter);
    const visible  = filtered.slice(-DOM_CAP);

    viewer.innerHTML = visible.length > 0
        ? visible.map(formatEntry).join('')
        : '<div style="padding:20px; color:#606060; text-align:center; font-style:italic;">No entries match the current filter.</div>';

    updateStats();

    if (autoScroll) viewer.scrollTop = viewer.scrollHeight;
}

/**
 * Incremental append for a single new real-time entry.
 * O(1) DOM operation — no full re-render.
 */
function appendEntry(entry) {
    // Memory cap: drop oldest to stay within MEM_CAP
    allEntries.push(entry);
    if (allEntries.length > MEM_CAP) {
        allEntries.splice(0, allEntries.length - MEM_CAP);
    }

    if (!matchesFilter(entry)) {
        updateStats();
        return;
    }

    const viewer = getViewer();
    if (!viewer) return;

    // DOM cap: remove oldest rendered row if over limit
    const rows = viewer.querySelectorAll('.log-entry');
    if (rows.length >= DOM_CAP) {
        rows[0].remove();
    }

    viewer.insertAdjacentHTML('beforeend', formatEntry(entry));
    updateStats();

    if (autoScroll) viewer.scrollTop = viewer.scrollHeight;
}

// ── Stats Footer ─────────────────────────────────────────────────────────────

function updateStats() {
    let errors = 0, warnings = 0;
    for (const e of allEntries) {
        if (e.category === 'ERROR') errors++;
        else if (e.category === 'WARNING') warnings++;
    }
    const last = allEntries.length > 0 ? allEntries[allEntries.length - 1].ts : '--';
    const el = id => document.getElementById(id);
    if (el('stat-total'))        el('stat-total').textContent        = allEntries.length.toLocaleString();
    if (el('stat-errors'))       el('stat-errors').textContent       = errors;
    if (el('stat-warnings'))     el('stat-warnings').textContent     = warnings;
    if (el('stat-last-updated')) el('stat-last-updated').textContent = last;
}

// ── Filter Button Helpers ─────────────────────────────────────────────────────

// Maps individual toggle button ids → filter group values
const TOGGLE_FILTER_MAP = {
    'btn-filter-events':  'event',
    'btn-filter-effects': 'render',
    'btn-filter-openrgb': 'openrgb',
    'btn-filter-errors':  'error',
};

function updateFilterButtons() {
    const allActive = [...ALL_FILTER_VALUES].every(f => activeFilters.has(f));
    const allBtn = document.getElementById('btn-filter-all');
    if (allBtn) allBtn.className = allActive ? BTN_ACTIVE : BTN_INACTIVE;

    Object.entries(TOGGLE_FILTER_MAP).forEach(([id, filter]) => {
        const btn = document.getElementById(id);
        if (btn) btn.className = activeFilters.has(filter) ? BTN_ACTIVE : BTN_INACTIVE;
    });
}

// ── API Calls ────────────────────────────────────────────────────────────────

async function loadInitialLogs() {
    const viewer = getViewer();
    if (viewer) viewer.innerHTML = `<div style="padding:20px; color:#606060; text-align:center; font-style:italic;">${(window.i18n && window.i18n.get('common.loading')) || 'Loading...'}</div>`;

    try {
        const result = await eel.get_logs()();
        if (result?.success) {
            allEntries = result.entries || [];
            // Enforce client-side cap on initial load too
            if (allEntries.length > MEM_CAP) {
                allEntries = allEntries.slice(-MEM_CAP);
            }
            renderLog();
        } else {
            if (viewer) viewer.innerHTML = `<div style="padding:20px; color:#F44336;">Failed to load logs: ${result?.error || 'unknown error'}</div>`;
        }
    } catch (e) {
        console.error('[Logs] Failed to load initial logs:', e);
        if (viewer) viewer.innerHTML = `<div style="padding:20px; color:#F44336;">${(window.i18n && window.i18n.get('common.backend_connection_failed')) || 'Failed to connect to backend.'}</div>`;
    }
}

// ── Real-Time Push from Python ────────────────────────────────────────────────

/**
 * Called by Python via eel.receive_log(entry).
 * Must be exposed BEFORE eel is fully connected (registered during page load).
 */
eel.expose(receive_log);
function receive_log(entry) {
    appendEntry(entry);
}

// ── Export ───────────────────────────────────────────────────────────────────

function exportLogs() {
    const lines = allEntries.map(e => `[${e.ts}] [${e.category}] ${e.message}`).join('\n');
    const blob  = new Blob([lines], { type: 'text/plain' });
    const url   = URL.createObjectURL(blob);
    const a     = document.createElement('a');
    const date  = new Date().toISOString().slice(0, 10);
    a.href     = url;
    a.download = `ed_event2led_logs_${date}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Initialisation ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {

    // ── Auto-scroll toggle ──────────────────────────────────────────────────
    const toggleAutoScroll = document.getElementById('toggle-autoscroll');
    if (toggleAutoScroll) {
        toggleAutoScroll.addEventListener('change', e => {
            autoScroll = e.target.checked;
            if (autoScroll) {
                const viewer = getViewer();
                if (viewer) viewer.scrollTop = viewer.scrollHeight;
            }
        });
    }

    // ── Clear logs ──────────────────────────────────────────────────────────
    document.getElementById('btn-clear-logs')?.addEventListener('click', async () => {
        await eel.clear_logs()();
        allEntries = [];
        renderLog();
    });

    // ── Filter buttons ──────────────────────────────────────────────────────
    document.getElementById('btn-filter-all')?.addEventListener('click', () => {
        activeFilters = new Set(ALL_FILTER_VALUES);
        updateFilterButtons();
        renderLog();
    });

    Object.entries(TOGGLE_FILTER_MAP).forEach(([id, filter]) => {
        document.getElementById(id)?.addEventListener('click', () => {
            if (activeFilters.has(filter)) {
                activeFilters.delete(filter);
            } else {
                activeFilters.add(filter);
            }
            updateFilterButtons();
            renderLog();
        });
    });

    // ── Search ───────────────────────────────────────────────────────────────
    document.getElementById('log-search')?.addEventListener('input', e => {
        searchText = e.target.value.toLowerCase().trim();
        renderLog();
    });

    // ── Export ───────────────────────────────────────────────────────────────
    document.getElementById('btn-export-logs')?.addEventListener('click', exportLogs);

    // ── Load initial data ────────────────────────────────────────────────────
    await loadInitialLogs();

    // ── i18n ─────────────────────────────────────────────────────────────────
    if (typeof initI18n === 'function') await initI18n();
    if (typeof applyI18n === 'function') applyI18n();

    // ── Fade in ───────────────────────────────────────────────────────────────
    document.body.classList.add('loaded');
});
