/**
 * settings.js
 * Settings page logic for code.html
 *
 * Handles:
 * - Loading/saving settings
 * - Language selection
 * - Theme selection
 * - OpenRGB connection testing
 * - Journal path verification
 */

// ========================================
// STATE
// ========================================

let currentSettings = {};
let selectedLanguage = 'en';
let selectedTheme = 'elite';

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', async function() {
    console.log('[Settings] Initializing...');

    // Load git info for footer
    loadGitInfo();

    // Load settings from backend
    await loadSettings();

    // Setup event listeners
    setupLanguageDropdown();
    setupThemeButtons();
    setupOpenRGBSection();
    setupJournalSection();
    setupSaveButton();

    console.log('[Settings] Initialization complete');
});

// ========================================
// GIT INFO (Footer)
// ========================================

async function loadGitInfo() {
    try {
        const info = await api('get_git_info');
        if (info) {
            const versionEl = document.getElementById('app-version');
            const buildEl = document.getElementById('app-build-date');

            if (versionEl) {
                let versionText = 'v' + info.version;
                if (info.is_dirty) {
                    versionText += ' (dirty)';
                }
                versionEl.textContent = versionText;
            }

            if (buildEl) {
                buildEl.textContent = info.build_date;
            }

            console.log('[Settings] Git info loaded:', info);
        }
    } catch (e) {
        console.warn('[Settings] Failed to load git info:', e);
    }
}

// ========================================
// LOAD SETTINGS
// ========================================

async function loadSettings() {
    console.log('[Settings] Loading settings from backend...');

    const result = await api('get_settings');

    if (!result || !result.language) {
        showNotification(window.i18n.get('notifications.failed_load_settings') || 'Failed to load settings', 'error');
        console.error('[Settings] Failed to load settings:', result);
        return;
    }

    currentSettings = result;
    console.log('[Settings] Loaded settings:', currentSettings);

    // Initialize i18n with user's language
    if (window.i18n) {
        await window.i18n.init(result.language);
    }

    // Populate UI with loaded settings
    populateLanguage(result.language);
    populateTheme(result.theme);
    await populateOpenRGB(result.openrgb_host, result.openrgb_port);
    populateJournalPath(result.journal_directory);

    showNotification(window.i18n ? window.i18n.get('notifications.settings_loaded') : 'Settings loaded', 'success');

    // Trigger fade-in AFTER translations are applied (prevents FOUC)
    requestAnimationFrame(function() {
        document.body.classList.add('loaded');
        console.log('[Settings] Page fade-in triggered (translations ready)');
    });
}

function populateLanguage(language) {
    selectedLanguage = language || 'en';

    // Update dropdown selected text
    const selectedSpan = document.getElementById('language-selected');
    const languageMap = {
        'en': 'English (United States)',
        'de': 'Deutsch',
        'fr': 'Français',
        'es': 'Español',
        'it': 'Italiano'
    };

    selectedSpan.textContent = languageMap[selectedLanguage] || 'English (United States)';

    // Mark selected item in dropdown
    const items = document.querySelectorAll('#language-dropdown .dropdown-item');
    items.forEach(item => {
        if (item.dataset.value === selectedLanguage) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

function populateTheme(theme) {
    selectedTheme = theme || 'elite';

    // Apply theme colors to CSS variables
    applyThemeColors(selectedTheme);

    // Update theme buttons styling
    const themeButtons = document.querySelectorAll('.theme-btn');
    themeButtons.forEach(btn => {
        if (btn.dataset.theme === selectedTheme) {
            // Active styling
            btn.classList.remove('border-white/10');
            btn.classList.add('border-2');
            btn.querySelector('.w-2.h-2').classList.remove('bg-white/20');
            btn.querySelector('.w-2.h-2').classList.add('bg-' + getThemeColorClass(selectedTheme));
        } else {
            // Inactive styling
            btn.classList.add('border-white/10');
            btn.classList.remove('border-2');
            btn.querySelector('.w-2.h-2').classList.add('bg-white/20');
        }
    });
}

function getThemeColorClass(theme) {
    const colorMap = {
        'elite': '[#FF6600]',
        'event2led': '[#7f13ec]',
        'dark': '[#14F5FF]',
        'light': '[#00FF41]'
    };
    return colorMap[theme] || '[#FF6600]';
}

// applyThemeColors() is defined globally in common.js and shared by all pages.

async function populateOpenRGB(host, port) {
    document.getElementById('openrgb-host').value = host || '127.0.0.1';
    document.getElementById('openrgb-port').value = port || 6742;

    // Auto-check connection status on page load (socket ping only, no side effects)
    const statusSpan = document.getElementById('openrgb-status');
    const statusIndicator = document.getElementById('openrgb-status-indicator');
    statusSpan.textContent = window.i18n.get('status_strings.checking') || 'Checking...';
    statusSpan.className = 'text-sm text-yellow-400 uppercase';
    statusIndicator.className = 'w-2 h-2 rounded-full bg-yellow-400 animate-pulse';

    const status = await api('get_openrgb_status');

    if (status && status.reachable) {
        statusSpan.textContent = window.i18n.get('status_strings.server_reachable') || 'Status: Server Reachable';
        statusSpan.className = 'text-sm text-green-400 uppercase';
        statusIndicator.className = 'w-2 h-2 rounded-full bg-green-400';
    } else {
        statusSpan.textContent = window.i18n.get('status_strings.disconnected') || 'Status: Disconnected';
        statusSpan.className = 'text-sm text-red-400 uppercase';
        statusIndicator.className = 'w-2 h-2 rounded-full bg-red-400';
    }
}

function populateJournalPath(path) {
    const pathInput = document.getElementById('journal-path');
    pathInput.value = path || '';

    // Auto-verify if path exists
    if (path) {
        verifyJournalPath();
    }
}

// ========================================
// LANGUAGE DROPDOWN
// ========================================

function setupLanguageDropdown() {
    const dropdown = document.getElementById('language-dropdown');

    if (!dropdown) {
        console.error('[Settings] Language dropdown not found in DOM!');
        return;
    }

    const button = dropdown.querySelector('.dropdown-button');
    const menu = dropdown.querySelector('.dropdown-menu');
    const items = dropdown.querySelectorAll('.dropdown-item');
    const selectedSpan = document.getElementById('language-selected');

    console.log(`[Settings] Language dropdown setup: ${items.length} languages found`);

    // Toggle dropdown
    button.addEventListener('click', function(e) {
        e.stopPropagation();
        const wasHidden = menu.classList.contains('hidden');
        menu.classList.toggle('hidden');
        button.classList.toggle('active');

        console.log(`[Settings] Language dropdown ${wasHidden ? 'opened' : 'closed'}`);
    });

    // Select language
    items.forEach(item => {
        item.addEventListener('click', async function() {
            selectedLanguage = this.dataset.value;
            const languageName = this.textContent.trim();
            selectedSpan.textContent = languageName;

            // Update selected styling
            items.forEach(i => i.classList.remove('selected'));
            this.classList.add('selected');

            // Close dropdown
            menu.classList.add('hidden');
            button.classList.remove('active');

            console.log(`[Settings] Language changed to: ${selectedLanguage} (${languageName})`);

            // Apply translations immediately
            if (window.i18n) {
                await window.i18n.change(selectedLanguage);
            }
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!dropdown.contains(e.target)) {
            menu.classList.add('hidden');
            button.classList.remove('active');
        }
    });
}

// ========================================
// THEME BUTTONS
// ========================================

function setupThemeButtons() {
    const themeButtons = document.querySelectorAll('.theme-btn');

    themeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            selectedTheme = this.dataset.theme;
            console.log('[Settings] Theme changed to:', selectedTheme);

            // Update UI
            populateTheme(selectedTheme);
        });
    });
}

// ========================================
// OPENRGB SECTION
// ========================================

function setupOpenRGBSection() {
    const testBtn = document.getElementById('test-connection-btn');
    testBtn.addEventListener('click', testOpenRGB);
}

async function testOpenRGB() {
    const btn = document.getElementById('test-connection-btn');
    const statusSpan = document.getElementById('openrgb-status');
    const statusIndicator = document.getElementById('openrgb-status-indicator');

    // Disable button during test
    btn.disabled = true;
    const originalText = btn.querySelector('.orbitron').textContent;
    btn.querySelector('.orbitron').textContent = window.i18n.get('status_strings.testing') || 'TESTING...';

    console.log('[Settings] Testing OpenRGB connection...');

    const result = await api('test_openrgb_connection');

    if (result && result.connected) {
        // Success
        statusSpan.textContent = window.i18n.interpolate('status_strings.connected_devices', {count: result.device_count}) || `Status: Connected (${result.device_count} device(s))`;
        statusSpan.className = 'text-sm text-green-400 uppercase';
        statusIndicator.className = 'w-2 h-2 rounded-full bg-green-400 glow-orange';

        showNotification(window.i18n.interpolate('notifications.openrgb_ok_count', {count: result.device_count}) || `OpenRGB OK! ${result.device_count} device(s) found`, 'success');
        console.log('[Settings] OpenRGB connected:', result);
    } else {
        // Failure
        statusSpan.textContent = window.i18n.get('status_strings.disconnected') || 'Status: Disconnected';
        statusSpan.className = 'text-sm text-red-400 uppercase';
        statusIndicator.className = 'w-2 h-2 rounded-full bg-red-400';

        showNotification(result?.message || window.i18n.get('notifications.openrgb_failed') || 'Connection failed', 'error');
        console.error('[Settings] OpenRGB connection failed:', result);
    }

    // Re-enable button
    btn.disabled = false;
    btn.querySelector('.orbitron').textContent = originalText;
}

// ========================================
// JOURNAL SECTION
// ========================================

function setupJournalSection() {
    const browseBtn = document.getElementById('browse-btn');
    const verifyBtn = document.getElementById('verify-path-btn');
    const pathInput = document.getElementById('journal-path');

    browseBtn.addEventListener('click', browseJournalDirectory);
    verifyBtn.addEventListener('click', verifyJournalPath);

    // Auto-verify when user manually types/pastes and then leaves the field
    pathInput.addEventListener('blur', function() {
        if (pathInput.value.trim()) {
            verifyJournalPath();
        }
    });
}

async function browseJournalDirectory() {
    console.log('[Settings] Opening file dialog...');

    const path = await api('browse_journal_directory');

    if (path) {
        console.log('[Settings] User selected path:', path);
        document.getElementById('journal-path').value = path;

        // Auto-verify after selection
        verifyJournalPath();
    } else {
        console.log('[Settings] User cancelled file dialog');
    }
}

async function verifyJournalPath() {
    const pathInput = document.getElementById('journal-path');
    const path = pathInput.value;

    if (!path) {
        showNotification(window.i18n.get('notifications.please_select_journal_path') || 'Please enter or select a journal path first', 'warning');
        return;
    }

    const statusSpan = document.getElementById('journal-status');
    const statusIndicator = document.getElementById('journal-status-indicator');

    console.log('[Settings] Verifying journal path:', path);

    // Show verifying state
    statusSpan.textContent = window.i18n.get('status_strings.verifying') || 'Status: Verifying...';
    statusSpan.className = 'text-sm text-yellow-400 uppercase';
    statusIndicator.className = 'w-2 h-2 rounded-full bg-yellow-400 animate-pulse';

    const result = await api('verify_journal_path', path);

    if (result && result.valid) {
        // Success
        // get(key, vars) translates AND fills {{count}}; interpolate() expects a text, not a key
        statusSpan.textContent = window.i18n.get('status_strings.verified_files', {count: result.file_count}) || `Status: Verified (${result.file_count} file(s))`;
        statusSpan.className = 'text-sm text-green-400 uppercase';
        statusIndicator.className = 'w-2 h-2 rounded-full bg-green-400';

        showNotification(window.i18n.get('notifications.path_verified_count', {count: result.file_count}) || `Path verified! Found ${result.file_count} journal file(s)`, 'success');
        console.log('[Settings] Journal path valid:', result);
    } else {
        // Failure
        statusSpan.textContent = window.i18n.get('status_strings.invalid_path') || 'Status: Invalid Path';
        statusSpan.className = 'text-sm text-red-400 uppercase';
        statusIndicator.className = 'w-2 h-2 rounded-full bg-red-400';

        showNotification(result?.message || window.i18n.get('notifications.path_invalid') || 'Invalid path', 'error');
        console.error('[Settings] Journal path invalid:', result);
    }
}

// ========================================
// SAVE SETTINGS
// ========================================

function setupSaveButton() {
    const saveBtn = document.getElementById('save-btn');
    saveBtn.addEventListener('click', saveSettings);
}

async function saveSettings() {
    console.log('[Settings] Saving settings...');

    // Collect settings from UI
    const settingsData = {
        language: selectedLanguage,
        theme: selectedTheme,
        openrgb_host: document.getElementById('openrgb-host').value,
        openrgb_port: parseInt(document.getElementById('openrgb-port').value),
        journal_directory: document.getElementById('journal-path').value,
        enable_new_ui: false // Keep PyQt6 setting for now
    };

    console.log('[Settings] Saving data:', settingsData);

    const result = await api('save_settings', settingsData);

    if (result && result.success) {
        showNotification(window.i18n.get('notifications.settings_saved') || 'Settings saved successfully!', 'success');
        console.log('[Settings] Settings saved');

        // Reload to refresh UI with new settings
        currentSettings = settingsData;
    } else {
        showNotification(result?.message || window.i18n.get('notifications.failed_save_settings') || 'Failed to save settings', 'error');
        console.error('[Settings] Save failed:', result);
    }
}

// ========================================
// UTILITY
// ========================================

console.log('[Settings] Module loaded');
