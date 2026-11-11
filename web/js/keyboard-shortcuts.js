/**
 * keyboard-shortcuts.js
 * Global keyboard shortcuts for ED:Event2Led
 *
 * Usage: Include this file in all pages. Set context with setShortcutContext('page-name').
 */

// Shortcut registry with descriptions
const SHORTCUTS = {
    // Global navigation (sempre disponibili)
    'Ctrl+H': { action: 'nav-home', description: 'Go to Home', global: true },
    'Ctrl+E': { action: 'nav-effects', description: 'Go to Effects Editor', global: true },
    'Ctrl+D': { action: 'nav-devices', description: 'Go to Devices', global: true },
    'Ctrl+K': { action: 'nav-keyboard', description: 'Go to Keyboard Designer', global: true },
    'Ctrl+M': { action: 'nav-events', description: 'Go to Event Mappings', global: true },

    // Context-aware actions
    'Ctrl+S': { action: 'save', description: 'Save current work', contextual: true },
    'Ctrl+T': { action: 'test', description: 'Test effect on hardware', contextual: true },
    'Ctrl+N': { action: 'new', description: 'Create new effect', contextual: true },
    'Ctrl+Space': { action: 'toggle-monitoring', description: 'Start/Stop monitoring', contextual: true },

    // Global helpers
    'F1': { action: 'help', description: 'Show keyboard shortcuts', global: true },
    'Escape': { action: 'close-modal', description: 'Close modal/cancel', global: true }
};

// Current page context (set by each page)
let _pageContext = null;

/**
 * Set page context for context-aware shortcuts
 * @param {string} context - 'home', 'effects-editor', 'events', etc.
 */
function setShortcutContext(context) {
    _pageContext = context;
    console.log(`[Shortcuts] Context set to: ${context}`);
}

// Global keydown listener
document.addEventListener('keydown', (e) => {
    // Build key combo string
    const combo = [
        e.ctrlKey && 'Ctrl',
        e.altKey && 'Alt',
        e.shiftKey && 'Shift',
        e.key === ' ' ? 'Space' : e.key
    ].filter(Boolean).join('+');

    const shortcut = SHORTCUTS[combo];
    if (!shortcut) return;

    // Check if user is typing in an input/textarea
    const activeElement = document.activeElement;
    const isTyping = activeElement && (
        activeElement.tagName === 'INPUT' ||
        activeElement.tagName === 'TEXTAREA' ||
        activeElement.isContentEditable
    );

    // Don't intercept if typing (except F1 and Escape which should always work)
    if (isTyping && combo !== 'F1' && combo !== 'Escape') {
        return;
    }

    // Prevent default only if we handle the shortcut
    e.preventDefault();

    // Dispatch action
    handleShortcutAction(shortcut.action);
});

/**
 * Handle shortcut action based on page context
 */
function handleShortcutAction(action) {
    console.log(`[Shortcuts] Action: ${action}, Context: ${_pageContext}`);

    switch (action) {
        // ── Global Navigation ────────────────────────────────────────
        case 'nav-home':
            window.location.href = 'index.html';
            break;

        case 'nav-effects':
            window.location.href = 'effects-lib.html';
            break;

        case 'nav-devices':
            window.location.href = 'devices.html';
            break;

        case 'nav-keyboard':
            window.location.href = 'keyboard-designer.html';
            break;

        case 'nav-events':
            window.location.href = 'events.html';
            break;

        // ── Context-Aware: Save ──────────────────────────────────────
        case 'save':
            if (_pageContext === 'effects-lib' && typeof saveEffect === 'function') {
                saveEffect();
                console.log('[Shortcuts] Save effect');
            } else if (_pageContext === 'events' && typeof saveCurrentMapping === 'function') {
                saveCurrentMapping();
                console.log('[Shortcuts] Save mapping');
            } else if (_pageContext === 'settings' && typeof saveSettings === 'function') {
                saveSettings();
                console.log('[Shortcuts] Save settings');
            } else if (_pageContext === 'keyboard-designer' && typeof saveKeyboardColors === 'function') {
                saveKeyboardColors();
                console.log('[Shortcuts] Save keyboard colors');
            } else {
                console.log('[Shortcuts] Save not available in this context');
            }
            break;

        // ── Context-Aware: Test ──────────────────────────────────────
        case 'test':
            if (_pageContext === 'effects-lib' && typeof testEffect === 'function') {
                testEffect();
                console.log('[Shortcuts] Test effect');
            } else {
                console.log('[Shortcuts] Test not available in this context');
            }
            break;

        // ── Context-Aware: New ───────────────────────────────────────
        case 'new':
            if (_pageContext === 'effects-lib' && typeof createNewEffect === 'function') {
                createNewEffect();
                console.log('[Shortcuts] Create new effect');
            } else {
                console.log('[Shortcuts] New not available in this context');
            }
            break;

        // ── Context-Aware: Toggle Monitoring ─────────────────────────
        case 'toggle-monitoring':
            if (_pageContext === 'home' && typeof toggleMonitoring === 'function') {
                toggleMonitoring();
                console.log('[Shortcuts] Toggle monitoring');
            } else {
                console.log('[Shortcuts] Toggle monitoring only available on home page');
            }
            break;

        // ── Global Helpers ───────────────────────────────────────────
        case 'close-modal':
            // Close any visible modal
            const modals = document.querySelectorAll('[id$="-modal"]:not(.hidden), .modal:not(.hidden)');
            if (modals.length > 0) {
                modals.forEach(modal => {
                    modal.classList.add('hidden');
                });
                console.log('[Shortcuts] Closed modal');
            }
            break;

        case 'help':
            showKeyboardShortcutsHelp();
            break;

        default:
            console.warn(`[Shortcuts] Unhandled action: ${action}`);
    }
}

/**
 * Show keyboard shortcuts help modal
 */
function showKeyboardShortcutsHelp() {
    // Check if modal already exists
    let modal = document.getElementById('shortcuts-help-modal');

    if (!modal) {
        // Organize shortcuts by category
        const globalNav = Object.entries(SHORTCUTS).filter(([_, s]) => s.global && _.startsWith('Ctrl'));
        const contextual = Object.entries(SHORTCUTS).filter(([_, s]) => s.contextual);
        const helpers = Object.entries(SHORTCUTS).filter(([k, s]) => s.global && !k.startsWith('Ctrl'));

        // Create modal dynamically
        modal = document.createElement('div');
        modal.id = 'shortcuts-help-modal';
        modal.className = 'fixed inset-0 z-[10000] flex items-center justify-center bg-black/80';
        modal.innerHTML = `
            <div class="sci-fi-border carbon-pattern p-8 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <h2 class="orbitron text-2xl mb-6 text-[var(--primary-accent)]">⌨️ Keyboard Shortcuts</h2>

                <div class="mb-6">
                    <h3 class="text-sm uppercase tracking-widest text-white/60 mb-3">Navigation</h3>
                    <div class="grid grid-cols-2 gap-3">
                        ${globalNav.map(([key, {description}]) => `
                            <div class="flex items-center gap-3">
                                <kbd class="px-2 py-1 bg-black/50 border border-white/20 rounded text-sm font-mono whitespace-nowrap">${key}</kbd>
                                <span class="text-sm text-white/70">${description}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="mb-6">
                    <h3 class="text-sm uppercase tracking-widest text-white/60 mb-3">Context Actions</h3>
                    <div class="grid grid-cols-2 gap-3">
                        ${contextual.map(([key, {description}]) => `
                            <div class="flex items-center gap-3">
                                <kbd class="px-2 py-1 bg-black/50 border border-white/20 rounded text-sm font-mono whitespace-nowrap">${key}</kbd>
                                <span class="text-sm text-white/70">${description}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="mb-6">
                    <h3 class="text-sm uppercase tracking-widest text-white/60 mb-3">Global Helpers</h3>
                    <div class="grid grid-cols-2 gap-3">
                        ${helpers.map(([key, {description}]) => `
                            <div class="flex items-center gap-3">
                                <kbd class="px-2 py-1 bg-black/50 border border-white/20 rounded text-sm font-mono whitespace-nowrap">${key}</kbd>
                                <span class="text-sm text-white/70">${description}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <button onclick="document.getElementById('shortcuts-help-modal').remove()"
                        class="btn-sci-fi px-6 py-2 w-full text-sm uppercase">
                    Close (Esc)
                </button>
            </div>
        `;
        document.body.appendChild(modal);
    } else {
        // Show existing modal
        modal.classList.remove('hidden');
    }

    // Close on click outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Log initialization
console.log('[Shortcuts] Keyboard shortcuts system initialized');
