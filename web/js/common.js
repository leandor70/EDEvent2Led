/**
 * common.js
 * Shared utilities for all web pages
 *
 * Provides:
 * - API call wrapper with error handling
 * - Notification system
 * - Color conversion utilities
 */

/**
 * API call wrapper with automatic error handling.
 *
 * @param {string} funcName - Name of the Python @eel.expose function
 * @param  {...any} args - Arguments to pass to the function
 * @returns {Promise<object>} - Result object from Python
 *
 * @example
 * const result = await api('get_settings');
 * if (result.success) { ... }
 */
async function api(funcName, ...args) {
    try {
        // Check if eel is available
        if (typeof eel === 'undefined') {
            console.error('[API] Eel not loaded! Make sure <script src="/eel.js"> is included.');
            return { success: false, error: 'Eel not initialized' };
        }

        // Call Python function via Eel
        const result = await eel[funcName](...args)();

        // If result is null/undefined, return empty object
        return result || {};
    } catch (error) {
        console.error(`[API] Error calling ${funcName}:`, error);
        return {
            success: false,
            error: error.message || 'Connection lost or function not found'
        };
    }
}

/**
 * Show notification to user with visual toast + console log.
 *
 * @param {string} message - Notification message
 * @param {string} type - Notification type: 'info', 'success', 'warning', 'error'
 * @param {number} duration - Duration in ms (default: 4000, 0 = persistent)
 */
function showNotification(message, type = 'info', duration = 4000) {
    // Console log (for debugging)
    const prefix = `[${type.toUpperCase()}]`;
    const style = {
        'info': 'color: #3b82f6',
        'success': 'color: #10b981',
        'warning': 'color: #f59e0b',
        'error': 'color: #ef4444'
    }[type] || 'color: #6b7280';

    console.log(`%c${prefix} ${message}`, style);

    // Create toast container if not exists
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 12px;
            pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    // Icon mapping
    const icons = {
        'success': 'check_circle',
        'error': 'error',
        'warning': 'warning',
        'info': 'info'
    };

    // Color mapping
    const colors = {
        'success': '#10b981',
        'error': '#ef4444',
        'warning': '#f59e0b',
        'info': '#3b82f6'
    };

    toast.innerHTML = `
        <div style="
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(0, 0, 0, 0.95);
            border: 1px solid ${colors[type]};
            border-radius: 8px;
            padding: 12px 16px;
            min-width: 280px;
            max-width: 400px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            pointer-events: auto;
            animation: slideInRight 0.3s ease-out;
        ">
            <span class="material-symbols-outlined" style="color: ${colors[type]}; font-size: 24px;">
                ${icons[type] || 'info'}
            </span>
            <span style="color: white; flex: 1; font-size: 14px;">
                ${escapeHtml(message)}
            </span>
            <button onclick="this.parentElement.parentElement.remove()" style="
                background: none;
                border: none;
                color: rgba(255, 255, 255, 0.5);
                cursor: pointer;
                padding: 0;
                font-size: 20px;
            ">×</button>
        </div>
    `;

    container.appendChild(toast);

    // Auto-dismiss (if duration > 0)
    if (duration > 0) {
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// Add CSS animations for toast (run once)
if (!document.getElementById('toast-animations')) {
    const style = document.createElement('style');
    style.id = 'toast-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

/**
 * Convert hex color to RGB array.
 *
 * @param {string} hex - Hex color string (e.g., "#FF6600" or "FF6600")
 * @returns {[number, number, number]|null} - RGB array [r, g, b] or null if invalid
 *
 * @example
 * hexToRgb("#FF6600") // -> [255, 102, 0]
 */
function hexToRgb(hex) {
    // Remove # if present
    hex = hex.replace(/^#/, '');

    // Parse hex string
    const result = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);

    if (!result) {
        console.warn(`[Color] Invalid hex color: ${hex}`);
        return null;
    }

    return [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ];
}

/**
 * Convert RGB values to hex color string.
 *
 * @param {number} r - Red (0-255)
 * @param {number} g - Green (0-255)
 * @param {number} b - Blue (0-255)
 * @returns {string} - Hex color string with # prefix (e.g., "#FF6600")
 *
 * @example
 * rgbToHex(255, 102, 0) // -> "#FF6600"
 */
function rgbToHex(r, g, b) {
    // Clamp values to 0-255 range
    r = Math.max(0, Math.min(255, Math.round(r)));
    g = Math.max(0, Math.min(255, Math.round(g)));
    b = Math.max(0, Math.min(255, Math.round(b)));

    // Convert to hex with padding
    const hex = "#" + ((1 << 24) + (r << 16) + (g << 8) + b)
        .toString(16)
        .slice(1)
        .toUpperCase();

    return hex;
}

/**
 * Debounce function - delays execution until after wait time has elapsed
 * since the last time it was invoked.
 *
 * Useful for input fields, resize handlers, etc.
 *
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 *
 * @example
 * const debouncedSearch = debounce(searchEffects, 300);
 * input.addEventListener('input', debouncedSearch);
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format timestamp for display.
 *
 * @param {string} timestamp - ISO 8601 timestamp
 * @returns {string} - Formatted timestamp (HH:MM:SS)
 *
 * @example
 * formatTimestamp("2026-02-15T14:30:00Z") // -> "14:30:00"
 */
function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        return timestamp;
    }
}

/**
 * Escape HTML to prevent XSS (text content only).
 *
 * @param {string} text - Text to escape
 * @returns {string} - Escaped HTML-safe text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Escape a value for use inside an HTML attribute (e.g. title="..." value="...").
 * Encodes &, ", ', <, > so the attribute cannot break out of its quotes.
 *
 * @param {string} text
 * @returns {string}
 */
function escapeAttr(text) {
    return String(text ?? '')
        .replace(/&/g,  '&amp;')
        .replace(/"/g,  '&quot;')
        .replace(/'/g,  '&#39;')
        .replace(/</g,  '&lt;')
        .replace(/>/g,  '&gt;');
}

// ── Theme system ──────────────────────────────────────────────────────────────

const THEME_COLORS = {
    'elite':     { primary: '#FF6600', border: 'rgba(255,102,0,0.3)',   glow: 'rgba(255,102,0,0.05)'   },
    'event2led': { primary: '#7f13ec', border: 'rgba(127,19,236,0.3)',  glow: 'rgba(127,19,236,0.05)'  },
    'dark':      { primary: '#14F5FF', border: 'rgba(20,245,255,0.3)',  glow: 'rgba(20,245,255,0.05)'  },
    'light':     { primary: '#00FF41', border: 'rgba(0,255,65,0.3)',    glow: 'rgba(0,255,65,0.05)'    },
};

/**
 * Apply a theme palette to the whole page via CSS custom properties.
 * Also updates .sci-fi-border glow which needs an inline boxShadow override.
 * Called on every page load (from load-navigation.js) and on live
 * theme changes (from settings.js).
 */
function applyThemeColors(theme) {
    const colors = THEME_COLORS[theme] || THEME_COLORS['elite'];
    document.documentElement.style.setProperty('--primary-accent', colors.primary);
    document.documentElement.style.setProperty('--border-color',   colors.border);
    document.querySelectorAll('.sci-fi-border').forEach(el => {
        el.style.boxShadow = `0 0 15px rgba(0,0,0,0.5), inset 0 0 20px ${colors.glow}`;
    });
}

/**
 * Fetch the saved theme from the backend and apply it.
 * Fires-and-forgets; fails silently if Eel is not yet ready.
 */
async function loadAndApplyTheme() {
    if (typeof eel === 'undefined') return;
    try {
        const result = await eel.get_settings()();
        if (result?.theme) applyThemeColors(result.theme);
    } catch (_) {
        // Default CSS theme already in place — no action needed
    }
}

// ── Server shutdown guard ─────────────────────────────────────────────────────

// Cancel any pending server shutdown when this page connects.
// The close_callback fires on disconnect but NOT on reconnect, so each page
// must explicitly tell the server "I'm here, don't shut down."
document.addEventListener('DOMContentLoaded', function() {
    if (typeof eel !== 'undefined') {
        eel.cancel_shutdown()();
    }
});

// ── Performance: Pause animations when window loses focus ────────────────────

/**
 * Pause CSS animations and stop polling when window blurs (Alt+Tab to game).
 * Resume everything when window regains focus.
 *
 * Benefit: -90% GPU/CPU usage when app is in background.
 */

// Pause animations + dispatch blur event
window.addEventListener('blur', () => {
    document.body.style.animationPlayState = 'paused';
    _pollingPaused = true;
    window.dispatchEvent(new Event('app-window-blurred'));
});

// Resume animations + dispatch focus event
window.addEventListener('focus', () => {
    document.body.style.animationPlayState = 'running';
    _pollingPaused = false;
    window.dispatchEvent(new Event('app-window-focused'));
    // Immediate poll on focus restore so UI is up-to-date right away
    _pollConnectionStatus();
});

// ── Background Image Rotation ─────────────────────────────────────────────────

/**
 * Available background images in web/images/backgrounds/
 * Update this array when adding new background images.
 */
const BACKGROUND_IMAGES = [
    'spiral-galaxy.jpg',
    'Installation.png',
    'Coriolis.png',
    'Ship.png',
    'IcyLandscape.png'
];

/**
 * Select a random background image from the available backgrounds.
 * Changes background on every page load/navigation.
 */
function setRandomBackground() {
    const randomIndex = Math.floor(Math.random() * BACKGROUND_IMAGES.length);
    const selectedImage = BACKGROUND_IMAGES[randomIndex];
    const bgPath = `images/backgrounds/${selectedImage}`;

    // Find background image element (common pattern across all pages)
    const bgImg = document.querySelector('img[alt="Spiral Galaxy Background"]');

    if (bgImg) {
        bgImg.src = bgPath;
        console.log(`[Background] Random background selected: ${selectedImage}`);
    } else {
        console.warn('[Background] Background image element not found');
    }
}

// Apply random background on page load (runs BEFORE DOMContentLoaded)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setRandomBackground);
} else {
    // DOM already loaded (in case script loads late)
    setRandomBackground();
}

/**
 * Throttle function - executes at most once every N ms.
 * Use for: sliders, scroll, mousemove (real-time feedback with rate limit)
 *
 * @param {Function} func - Function to throttle
 * @param {number} limit - Minimum milliseconds between executions
 * @returns {Function} - Throttled function
 *
 * @example
 * const throttledUpdate = throttle(() => updatePreview(), 100);
 * slider.addEventListener('input', throttledUpdate);
 */
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ── Manual System ─────────────────────────────────────────────────────────────

/**
 * Open user manual at specific chapter (context-aware).
 *
 * @param {string} chapterId - Chapter ID to open (e.g., 'topology-editor')
 *
 * @example
 * // From topology-editor.html Help button:
 * openManual('topology-editor');
 *
 * // From effects-editor.html Help button:
 * openManual('effects-editor');
 */
function openManual(chapterId = 'introduction') {
    const lang = (window.i18n?.getCurrentLanguage?.() || 'it').toLowerCase();
    const supported = ['it', 'en', 'de', 'es', 'fr'];
    const file = supported.includes(lang) && lang !== 'it' ? `manual_${lang}.html` : 'manual.html';
    window.open(`${file}#${chapterId}`, '_blank', 'width=1400,height=900');
}

/**
 * Map current page to manual chapter ID.
 * Used to auto-detect which chapter to open from current page.
 *
 * @returns {string} - Chapter ID for current page
 */
function getCurrentPageChapterId() {
    const page = window.location.pathname.split('/').pop().replace('.html', '');

    const pageToChapter = {
        'index': 'home-dashboard',
        'effects-lib': 'effects-editor',
        'events': 'events',
        'keyboard-designer': 'keyboard-designer',
        'topology-editor': 'topology-editor',
        'status': 'status',
        'devices': 'devices',
        'test': 'test',
        'log': 'log',
        'code': 'settings'
    };

    return pageToChapter[page] || 'introduction';
}

/**
 * Open manual at chapter corresponding to current page.
 * Convenience function for generic Help buttons.
 */
function openManualForCurrentPage() {
    openManual(getCurrentPageChapterId());
}

// ── OpenRGB Reconnection UI (Tier 2 + Tier 3) ──────────────────

/**
 * TIER 2: Reconnection Toast Notifications
 */

window.show_reconnect_toast = function() {
    // Check if a reconnect toast already exists
    const container = document.getElementById('toast-container');
    if (container) {
        const existingToasts = container.querySelectorAll('.toast-info');
        for (const toast of existingToasts) {
            if (toast.textContent.includes('Attempting to reconnect')) {
                console.log('[Common] Reconnect toast already visible, skipping duplicate');
                return;  // Early return to prevent duplicate
            }
        }
    }

    console.log('[Common] Showing blue reconnect toast (persistent)');
    showNotification(
        window.i18n.get('notifications.reconnecting_openrgb') || 'Attempting to reconnect to OpenRGB...',
        'info',
        0  // Persistent until cleared
    );
};

window.show_reconnect_success_toast = function() {
    console.log('[Common] show_reconnect_success_toast() called');

    // Clear existing reconnect toasts
    const container = document.getElementById('toast-container');
    if (container) {
        const reconnectToasts = container.querySelectorAll('.toast-info');
        console.log(`[Common] Found ${reconnectToasts.length} info toasts to check`);
        reconnectToasts.forEach(toast => {
            if (toast.textContent.includes('reconnect')) {
                console.log('[Common] Removing reconnect toast:', toast.textContent.substring(0, 50));
                toast.remove();
            }
        });
    }

    console.log('[Common] Showing green success toast');
    showNotification(
        window.i18n.get('notifications.reconnected_openrgb') || 'Successfully reconnected to OpenRGB',
        'success',
        3000
    );
};

/**
 * TIER 2: Reconnection Status Polling
 * Monitors OpenRGB connection status and shows/hides toasts automatically
 */

let _lastConnectionState = null;
let _pollingActive = false;
let _pollingPaused = false;      // True when window is blurred (game in foreground)
let _reconnectingLocally = false;  // Flag to prevent multiple concurrent reconnection triggers

async function _pollConnectionStatus() {
    if (_pollingPaused) return;  // Window blurred — skip entirely, will resume on focus
    try {
        const status = await api('get_openrgb_connection_status');

        // TIER 3: Check FIRST (before any early returns) for connection lost modal trigger
        try {
            const lostStatus = await api('get_connection_lost_status');
            if (lostStatus.triggered) {
                window.show_openrgb_connection_lost_modal();
                await api('clear_connection_lost_status');
            }
        } catch (err) {
            console.error('[Common] Failed to check connection lost status:', err);
        }

        // Detect state transition: disconnected → connected
        if (_lastConnectionState === false && status.connected === true) {
            window.show_reconnect_success_toast();
            _reconnectingLocally = false;
        }

        // Detect state transition: connected → disconnected
        if (_lastConnectionState === true && status.connected === false) {
            // Don't trigger if already reconnecting (backend or local)
            if (status.reconnecting || _reconnectingLocally) {
                _lastConnectionState = status.connected;
                return;
            }

            _reconnectingLocally = true;

            try {
                await api('invalidate_openrgb_connection');
            } catch (err) {
                console.error('[Common] Failed to invalidate connection:', err);
                _reconnectingLocally = false;
                _lastConnectionState = status.connected;
                return;
            }

            window.show_reconnect_toast();

            try {
                await api('trigger_auto_reconnect');
            } catch (err) {
                console.error('[Common] Failed to trigger auto-reconnection:', err);
                _reconnectingLocally = false;
            }
        }

        _lastConnectionState = status.connected;

    } catch (error) {
        console.error('[Common] Connection status polling error:', error);
    } finally {
        // Adaptive interval: slow poll (3s) when stable, fast (1s) when unstable
        const interval = (_lastConnectionState === true) ? 3000 : 1000;
        setTimeout(_pollConnectionStatus, interval);
    }
}

// Start polling when page loads
window.addEventListener('DOMContentLoaded', () => {
    if (!_pollingActive) {
        _pollingActive = true;
        setTimeout(_pollConnectionStatus, 1000);  // First poll after 1s
    }
});

/**
 * UPDATE CHECK
 * The backend asks GitHub for the latest release at startup (api/update_api.py).
 * When a newer version exists, show one toast per browser session with a link to
 * the release page and a "don't remind me" button for that version.
 */

const _UPDATE_TOAST_KEY = 'e2l_update_toast_shown';

function _t(key, fallback, vars) {
    const s = (window.i18n && window.i18n.isLoaded && window.i18n.isLoaded()) ? window.i18n.get(key, vars) : null;
    if (s && s !== key) return s;
    return vars ? fallback.replace(/\{\{(\w+)\}\}/g, (_, k) => vars[k] ?? '') : fallback;
}

function showUpdateToast(info) {
    if (document.getElementById('update-toast')) return;
    const url = /^https:\/\/github\.com\//.test(info.url || '') ? info.url : 'https://github.com/leandor70/EDEvent2Led/releases';
    const latest = String(info.latest || '').replace(/^v/, '');
    const current = String(info.current || '').replace(/^v/, '').split('-')[0];
    const accent = 'var(--primary-accent, #3b82f6)';

    console.log(`[Update] New version available: ${latest} (running ${current})`);
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed; top:24px; right:24px; z-index:10000; display:flex; flex-direction:column; gap:12px; pointer-events:none;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.id = 'update-toast';
    toast.innerHTML = `
        <div style="display:flex; gap:12px; align-items:flex-start; background:rgba(0,0,0,0.95);
                    border:1px solid ${accent}; border-radius:8px; padding:12px 16px; min-width:280px;
                    max-width:400px; box-shadow:0 10px 40px rgba(0,0,0,0.5); pointer-events:auto;
                    animation:slideInRight 0.3s ease-out;">
            <span class="material-symbols-outlined" style="color:${accent}; font-size:24px;">system_update</span>
            <div style="flex:1; color:white; font-size:14px;">
                <div style="font-weight:600; margin-bottom:4px;">${escapeHtml(_t('notifications.update_available', 'New version {{latest}} available', { latest }))}</div>
                <div style="color:rgba(255,255,255,0.6); font-size:12px; margin-bottom:10px;">${escapeHtml(_t('notifications.update_current', 'You are running {{current}}', { current }))}</div>
                <div style="display:flex; gap:12px; align-items:center;">
                    <a href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer"
                       style="color:${accent}; font-weight:600; text-decoration:underline;">${escapeHtml(_t('notifications.update_download', 'Open release page'))}</a>
                    <button type="button" data-action="skip" style="background:none; border:none; padding:0; cursor:pointer;
                            color:rgba(255,255,255,0.5); font-size:12px;">${escapeHtml(_t('notifications.update_skip', "Don't remind me for this version"))}</button>
                </div>
            </div>
            <button type="button" data-action="close" style="background:none; border:none; color:rgba(255,255,255,0.5);
                    cursor:pointer; padding:0; font-size:20px;">×</button>
        </div>`;
    const close = () => {
        toast.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    };
    toast.querySelector('[data-action="close"]').addEventListener('click', close);
    toast.querySelector('[data-action="skip"]').addEventListener('click', () => {
        api('dismiss_update', info.latest);
        close();
    });
    container.appendChild(toast);
}

async function _checkForUpdate(attempt = 0) {
    const status = await api('get_update_status');
    if (status.state === 'pending' && attempt < 15) {
        setTimeout(() => _checkForUpdate(attempt + 1), 2000);
        return;
    }
    if (status.state !== 'available') return;
    try { sessionStorage.setItem(_UPDATE_TOAST_KEY, '1'); } catch (e) { /* storage blocked: may show again */ }
    showUpdateToast(status);
}

window.addEventListener('DOMContentLoaded', () => {
    let shown = false;
    try { shown = sessionStorage.getItem(_UPDATE_TOAST_KEY) === '1'; } catch (e) { /* ignore */ }
    if (!shown) setTimeout(_checkForUpdate, 3000);   // after the page and i18n settle
});

/**
 * TIER 3: Connection Lost Modal
 */

window.show_openrgb_connection_lost_modal = function() {
    // Remove existing modal
    const existing = document.getElementById('openrgb-lost-modal');
    if (existing) existing.remove();

    // Create modal
    const modal = document.createElement('div');
    modal.id = 'openrgb-lost-modal';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.9); display: flex; align-items: center;
        justify-content: center; z-index: 99999; animation: fadeIn 0.3s;
    `;

    modal.innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(20,20,30,0.95), rgba(10,10,20,0.95));
                    border: 2px solid #ef4444; border-radius: 16px; padding: 32px;
                    max-width: 500px; width: 90%; box-shadow: 0 20px 80px rgba(239,68,68,0.5);
                    animation: scaleIn 0.3s;">

            <div style="text-align: center; margin-bottom: 24px;">
                <span class="material-symbols-outlined" style="font-size: 72px; color: #ef4444;
                      filter: drop-shadow(0 0 20px rgba(239,68,68,0.5));">error</span>
            </div>

            <h2 style="color: #ef4444; font-size: 24px; font-weight: 600; margin: 0 0 16px 0; text-align: center;">
                ${(window.i18n && window.i18n.get('common.openrgb_connection_lost_title')) || 'OpenRGB Connection Lost'}
            </h2>

            <p style="color: rgba(255,255,255,0.8); font-size: 16px; line-height: 1.6; margin: 0 0 32px 0; text-align: center;">
                ${(window.i18n && window.i18n.get('common.openrgb_connection_lost_msg')) || 'The connection to OpenRGB server has been lost and automatic reconnection failed.'}
                <br><br>
                <strong style="color: white;">${(window.i18n && window.i18n.get('common.openrgb_connection_lost_hint')) || 'Please verify OpenRGB is running'}</strong> ${(window.i18n && window.i18n.get('common.openrgb_connection_lost_hint2')) || 'and click Retry Connection.'}
            </p>

            <div style="display: flex; gap: 12px; justify-content: center;">
                <button id="modal-retry-btn" style="background: linear-gradient(135deg, #3b82f6, #2563eb);
                        border: 1px solid #60a5fa; color: white; padding: 12px 24px; border-radius: 8px;
                        font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s;
                        box-shadow: 0 4px 16px rgba(59,130,246,0.3);">
                    <span class="material-symbols-outlined" style="vertical-align: middle; margin-right: 8px;">refresh</span>
                    ${(window.i18n && window.i18n.get('common.retry_connection')) || 'Retry Connection'}
                </button>

                <button id="modal-settings-btn" style="background: linear-gradient(135deg, rgba(75,85,99,0.5), rgba(55,65,81,0.5));
                        border: 1px solid rgba(156,163,175,0.3); color: white; padding: 12px 24px; border-radius: 8px;
                        font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                    <span class="material-symbols-outlined" style="vertical-align: middle; margin-right: 8px;">settings</span>
                    ${(window.i18n && window.i18n.get('common.go_to_settings_btn')) || 'Go to Settings'}
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    document.getElementById('modal-retry-btn').addEventListener('click', async function() {
        this.disabled = true;
        this.innerHTML = `<span class="material-symbols-outlined rotating">refresh</span> ${(window.i18n && window.i18n.get('common.connecting')) || 'Connecting...'}`;

        const result = await api('force_openrgb_reconnect');

        if (result.success) {
            showNotification(window.i18n.get('notifications.reconnected_openrgb') || 'Successfully reconnected to OpenRGB', 'success');
            modal.remove();
        } else {
            this.disabled = false;
            this.innerHTML = `<span class="material-symbols-outlined">refresh</span> ${(window.i18n && window.i18n.get('common.retry_connection')) || 'Retry Connection'}`;
            showNotification(window.i18n.interpolate('notifications.reconnection_failed', {error: result.error || 'Unknown error'}) || `Reconnection failed: ${result.error || 'Unknown error'}`, 'error');
        }
    });

    document.getElementById('modal-settings-btn').addEventListener('click', function() {
        window.location.href = 'code.html';
    });

    // Add animations CSS
    if (!document.getElementById('modal-animations')) {
        const style = document.createElement('style');
        style.id = 'modal-animations';
        style.textContent = `
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes scaleIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
            @keyframes rotating { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .rotating { animation: rotating 1s linear infinite; display: inline-block; }
        `;
        document.head.appendChild(style);
    }
};

// Log initialization
console.log('[Common] Utilities loaded');
