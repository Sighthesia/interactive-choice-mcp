/**
 * config.js - Configuration and settings management
 * Handles theme, language, notifications, and settings persistence
 */

// Section: Theme Management
const themeSelect = document.getElementById('themeSelect');
const htmlElement = document.documentElement;

/**
 * Apply a theme setting
 * @param {string} theme - 'light', 'dark', or 'system'
 */
function applyTheme(theme) {
    if (theme === 'system') {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        htmlElement.classList.toggle('dark', isDark);
    } else {
        htmlElement.classList.toggle('dark', theme === 'dark');
    }
    localStorage.setItem('mcp-theme', theme);
    if (themeSelect) themeSelect.value = theme;
}

// Section: Settings Helpers
function isSingleSubmit() {
    const el = document.getElementById('singleSubmitMode');
    return el ? el.checked : false;
}

function isUseDefaultOption() {
    const el = document.getElementById('useDefaultOption');
    return el ? el.checked : false;
}

function isAnnotationEnabled() {
    return window.mcpState.annotationEnabled;
}

function isPlaceholderVisible() {
    return window.mcpState.placeholderVisible;
}

// Section: Settings Persistence
/**
 * Track if interface was explicitly changed by user
 */
let transportExplicitlyChanged = false;

/**
 * Save global settings to server
 */
async function saveGlobalSettings() {
    const config = {
        timeout_seconds: parseInt(document.getElementById('timeoutInput')?.value || '60', 10),
        single_submit_mode: document.getElementById('singleSubmitMode')?.checked || false,
        use_default_option: document.getElementById('useDefaultOption')?.checked || false,
        timeout_action: document.getElementById('timeoutActionSelect')?.value || 'submit',
        language: window.mcpState.currentLang,
        notify_new: document.getElementById('notifyNew')?.checked ?? true,
        notify_upcoming: document.getElementById('notifyUpcoming')?.checked ?? true,
        upcoming_threshold: parseInt(document.getElementById('upcomingThreshold')?.value || '60', 10),
        notify_timeout: document.getElementById('notifyTimeout')?.checked ?? true,
        notify_if_foreground: document.getElementById('notifyIfForeground')?.checked ?? true,
        notify_if_focused: document.getElementById('notifyIfFocused')?.checked ?? true,
        notify_if_background: document.getElementById('notifyIfBackground')?.checked ?? true,
        notify_sound: document.getElementById('notifySound')?.checked ?? true,
    };
    // Only include interface if it was explicitly changed by the user
    if (transportExplicitlyChanged) {
        config.interface = document.getElementById('transportSelect')?.value || 'web';
    }
    console.log('[Settings] Saving config:', config);
    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        if (!res.ok) {
            console.error('[Settings] Failed to save settings:', await res.text());
        } else {
            console.log('[Settings] Config saved successfully');
        }
    } catch (e) {
        console.error('[Settings] Failed to save settings:', e);
    }
}

/**
 * Debounced save settings (500ms delay)
 */
function debouncedSaveSettings() {
    console.log('[Settings] debouncedSaveSettings called');
    if (window.mcpState.saveSettingsTimer) {
        clearTimeout(window.mcpState.saveSettingsTimer);
    }
    window.mcpState.saveSettingsTimer = setTimeout(saveGlobalSettings, 500);
}

// Section: Config Toggle
function toggleConfig() {
    const toggle = document.getElementById('configToggle');
    const content = document.getElementById('configContent');
    const card = toggle.closest('.card');
    const expanded = card.getAttribute('aria-expanded') === 'true';
    card.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    card.setAttribute('data-user-expanded', (!expanded).toString());
    toggle.classList.toggle('expanded', !expanded);
    content.classList.toggle('show', !expanded);
}

// Section: Config Highlight
function updateConfigHighlights() {
    const singleSubmit = document.getElementById('singleSubmitMode');
    const useDefault = document.getElementById('useDefaultOption');
    const itemSingle = document.getElementById('item-singleSubmitMode');
    const itemDefault = document.getElementById('item-useDefaultOption');

    if (itemSingle) itemSingle.classList.toggle('highlighted', singleSubmit?.checked);
    if (itemDefault) itemDefault.classList.toggle('highlighted', useDefault?.checked);
}

// Section: Collect Config
function collectConfig() {
    const defaults = window.mcpData.defaults;
    const rawTimeout = parseInt(document.getElementById('timeoutInput')?.value || defaults.timeout_seconds, 10);
    const timeout = Number.isFinite(rawTimeout) && rawTimeout > 0 ? rawTimeout : defaults.timeout_seconds;
    const transportSelect = document.getElementById('transportSelect');
    const interface = transportSelect ? transportSelect.value : 'web';
    const timeoutActionSelect = document.getElementById('timeoutActionSelect');
    const timeoutAction = timeoutActionSelect ? timeoutActionSelect.value : 'submit';
    return {
        interface,
        timeout_seconds: timeout,
        single_submit_mode: isSingleSubmit(),
        use_default_option: isUseDefaultOption(),
        timeout_action: timeoutAction,
    };
}

// Section: Initialize Config
function initializeConfig() {
    debugLog('Config', 'Initializing...');
    const defaults = window.mcpData.defaults;
    debugLog('Config', 'Defaults:', defaults);

    // Initialize theme
    const savedTheme = localStorage.getItem('mcp-theme') || 'system';
    applyTheme(savedTheme);

    // Initialize language
    const savedLang = localStorage.getItem('mcp-language') || defaults.language || 'en';
    applyLanguage(savedLang);

    // Initialize timeout action
    const timeoutActionSelect = document.getElementById('timeoutActionSelect');
    if (timeoutActionSelect) {
        timeoutActionSelect.value = defaults.timeout_action || 'submit';
    }

    // Initialize notification settings
    const notifySettings = [
        ['notifyNew', defaults.notify_new ?? true],
        ['notifyUpcoming', defaults.notify_upcoming ?? true],
        ['notifyTimeout', defaults.notify_timeout ?? true],
        ['notifyIfForeground', defaults.notify_if_foreground ?? true],
        ['notifyIfFocused', defaults.notify_if_focused ?? true],
        ['notifyIfBackground', defaults.notify_if_background ?? true],
        ['notifySound', defaults.notify_sound ?? true]
    ];

    notifySettings.forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.checked = value;
    });

    const upcomingThreshold = document.getElementById('upcomingThreshold');
    if (upcomingThreshold) upcomingThreshold.value = defaults.upcoming_threshold ?? 60;

    // Listen for theme changes
    if (themeSelect) {
        themeSelect.addEventListener('change', (e) => applyTheme(e.target.value));
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (themeSelect && themeSelect.value === 'system') {
            applyTheme('system');
        }
    });

    // Listen for language changes
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
        languageSelect.addEventListener('change', (e) => {
            applyLanguage(e.target.value);
            if (typeof renderOptions === 'function') renderOptions();
            debouncedSaveSettings();
        });
    }

    // Add listeners to global settings controls
    const settingsControls = [
        'singleSubmitMode', 'useDefaultOption',
        'timeoutActionSelect', 'notifyNew', 'notifyUpcoming',
        'upcomingThreshold', 'notifyTimeout', 'notifyIfForeground',
        'notifyIfFocused', 'notifyIfBackground', 'notifySound'
    ];

    settingsControls.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', debouncedSaveSettings);
    });

    // Transport select needs special handling to track explicit changes
    const transportSelect = document.getElementById('transportSelect');
    if (transportSelect) {
        transportSelect.addEventListener('change', () => {
            transportExplicitlyChanged = true;
            debouncedSaveSettings();
        });
    }

    // Timeout input change handler
    const timeoutInput = document.getElementById('timeoutInput');
    if (timeoutInput) {
        timeoutInput.addEventListener('change', debouncedSaveSettings);
    }

    // Initialize config highlights
    updateConfigHighlights();
}
