/**
 * i18n.js
 * Internationalization module for ED:Event2Led
 *
 * Features:
 * - Loads JSON translation files from config/i18n/
 * - Applies translations to elements with data-i18n attributes
 * - Supports variable interpolation ({{variable}})
 * - Automatic language switching
 */

// ========================================
// STATE
// ========================================

let currentLanguage = 'en';
let translations = {};
let isLoaded = false;

// ========================================
// INITIALIZATION
// ========================================

/**
 * Initialize i18n module with specified language.
 *
 * @param {string} language - Language code (en, it, de, fr, es)
 * @returns {Promise<boolean>} - Success status
 */
async function initI18n(language = 'en') {
    console.log(`[i18n] Initializing with language: ${language}`);

    const success = await loadLanguage(language);

    if (success) {
        applyTranslations();
        isLoaded = true;

        // Expose translations globally for other scripts
        window.i18nData = translations;

        // Trigger custom event for modules waiting on i18n
        window.dispatchEvent(new Event('i18nLoaded'));

        console.log('[i18n] Initialization complete');
    } else {
        console.error('[i18n] Initialization failed');
    }

    return success;
}

// ========================================
// LANGUAGE LOADING
// ========================================

/**
 * Load translation file for specified language.
 *
 * @param {string} language - Language code
 * @returns {Promise<boolean>} - Success status
 */
async function loadLanguage(language) {
    try {
        const response = await fetch(`/config/i18n/${language}.json`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        translations = await response.json();
        currentLanguage = language;

        console.log(`[i18n] Loaded ${language}.json successfully`);
        return true;
    } catch (error) {
        console.error(`[i18n] Failed to load ${language}.json:`, error);

        // Fallback to English if other language fails
        if (language !== 'en') {
            console.log('[i18n] Attempting fallback to English...');
            return await loadLanguage('en');
        }

        return false;
    }
}

/**
 * Change language at runtime.
 *
 * @param {string} language - New language code
 * @returns {Promise<boolean>} - Success status
 */
async function changeLanguage(language) {
    console.log(`[i18n] Changing language from ${currentLanguage} to ${language}`);

    const success = await loadLanguage(language);

    if (success) {
        applyTranslations();

        // Update global translations for other scripts
        window.i18nData = translations;

        console.log(`[i18n] Language changed to ${language}`);
    }

    return success;
}

// ========================================
// TRANSLATION APPLICATION
// ========================================

/**
 * Apply translations to all elements with data-i18n attribute.
 */
function applyTranslations() {
    const elements = document.querySelectorAll('[data-i18n]');
    let appliedCount = 0;

    elements.forEach(element => {
        const key = element.getAttribute('data-i18n');
        const value = getTranslation(key);

        if (value !== key) {
            // Check if element has data-i18n-vars for interpolation
            const vars = element.getAttribute('data-i18n-vars');

            if (vars) {
                try {
                    const varsObj = JSON.parse(vars);
                    element.textContent = interpolate(value, varsObj);
                } catch (e) {
                    console.warn(`[i18n] Invalid JSON in data-i18n-vars: ${vars}`);
                    element.textContent = value;
                }
            } else {
                element.textContent = value;
            }

            appliedCount++;
        } else {
            console.warn(`[i18n] Translation not found for key: ${key}`);
        }
    });

    // Apply translations to attributes (data-i18n-attr)
    const attrElements = document.querySelectorAll('[data-i18n-attr]');
    attrElements.forEach(element => {
        const attrMapping = element.getAttribute('data-i18n-attr');
        // Format: "attributeName:translation.key.path"
        // Example: "placeholder:sections.activity_logs.filter_placeholder"

        const pairs = attrMapping.split(',').map(pair => pair.trim());
        pairs.forEach(pair => {
            const [attrName, keyPath] = pair.split(':').map(s => s.trim());
            if (attrName && keyPath) {
                const value = getTranslation(keyPath);
                if (value !== keyPath) {
                    element.setAttribute(attrName, value);
                    appliedCount++;
                } else {
                    console.warn(`[i18n] Translation not found for attribute key: ${keyPath}`);
                }
            }
        });
    });

    console.log(`[i18n] Applied ${appliedCount} translations`);
}

/**
 * Get translation by key path.
 *
 * @param {string} keyPath - Dot-notation key path (e.g., "pages.configuration.title")
 * @param {Object} [vars] - Variables for interpolation
 * @returns {string} - Translated string or key if not found
 */
function getTranslation(keyPath, vars = null) {
    const keys = keyPath.split('.');
    let value = translations;

    for (const key of keys) {
        if (value && typeof value === 'object' && key in value) {
            value = value[key];
        } else {
            console.warn(`[i18n] Key not found: ${keyPath}`);
            return keyPath; // Return key as fallback
        }
    }

    // Interpolate variables if provided
    if (vars && typeof value === 'string') {
        return interpolate(value, vars);
    }

    return value;
}

/**
 * Interpolate variables in translation string.
 *
 * @param {string} template - Template string with {{variable}} placeholders
 * @param {Object} vars - Variables to interpolate
 * @returns {string} - Interpolated string
 *
 * @example
 * interpolate("Hello {{name}}!", {name: "World"})
 * // => "Hello World!"
 */
function interpolate(template, vars) {
    return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
        return key in vars ? vars[key] : match;
    });
}

/**
 * Public interpolate: accepts a template OR a translation key.
 *
 * Many callers pass a key (window.i18n.interpolate('notifications.x', {...})):
 * a plain interpolate would return the key itself and the user would see
 * "notifications.x". A string shaped like a key path that exists in the
 * translations is translated first, then its {{variables}} are filled.
 *
 * @param {string} templateOrKey - "Hello {{name}}" or "section.key"
 * @param {Object} [vars] - Variables to interpolate
 * @returns {string}
 */
function interpolateKeyOrTemplate(templateOrKey, vars = {}) {
    if (typeof templateOrKey !== 'string') return templateOrKey;
    if (/^\w+(\.\w+)+$/.test(templateOrKey)) {
        const value = getTranslation(templateOrKey);
        if (typeof value === 'string' && value !== templateOrKey) {
            return interpolate(value, vars || {});
        }
    }
    return interpolate(templateOrKey, vars || {});
}

// ========================================
// HELPER FUNCTIONS
// ========================================

/**
 * Translate a specific element.
 *
 * @param {HTMLElement} element - Element to translate
 * @param {string} keyPath - Translation key path
 * @param {Object} [vars] - Variables for interpolation
 */
function translateElement(element, keyPath, vars = null) {
    const value = getTranslation(keyPath, vars);

    if (value !== keyPath) {
        element.textContent = value;
    }
}

/**
 * Get current language code.
 *
 * @returns {string} - Current language code
 */
function getCurrentLanguage() {
    return currentLanguage;
}

/**
 * Check if i18n is loaded and ready.
 *
 * @returns {boolean} - Load status
 */
function isI18nLoaded() {
    return isLoaded;
}

/**
 * Get all translations for current language.
 *
 * @returns {Object} - Translations object
 */
function getAllTranslations() {
    return translations;
}

// ========================================
// EXPORT (for module usage)
// ========================================

// Make functions globally available
window.i18n = {
    init: initI18n,
    load: loadLanguage,
    change: changeLanguage,
    apply: applyTranslations,
    get: getTranslation,
    interpolate: interpolateKeyOrTemplate,
    translateElement: translateElement,
    getCurrentLanguage: getCurrentLanguage,
    isLoaded: isI18nLoaded,
    getAllTranslations: getAllTranslations
};

console.log('[i18n] Module loaded');
