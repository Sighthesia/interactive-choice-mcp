/**
 * bootstrap.js - Application bootstrap and data initialization
 * Reads server-injected JSON blocks into window.mcpData namespace
 */

// Section: Data Namespace
window.mcpData = {
    choiceId: null,
    defaults: {},
    options: [],
    sessionState: {},
    i18nTexts: {},
    promptType: null
};

// Section: Debug Helper
const DEBUG = true;
function debugLog(module, message, data) {
    if (DEBUG) {
        if (data !== undefined) {
            console.log('[' + module + '] ' + message, data);
        } else {
            console.log('[' + module + '] ' + message);
        }
    }
}
window.debugLog = debugLog;

// Section: Data Loading
(function initBootstrap() {
    debugLog('Bootstrap', 'Starting initialization...');

    // Read choice ID from JSON block
    const choiceIdEl = document.getElementById('mcp-choice-id');
    if (choiceIdEl) {
        try {
            window.mcpData.choiceId = JSON.parse(choiceIdEl.textContent);
            debugLog('Bootstrap', 'Loaded choiceId:', window.mcpData.choiceId);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse choice ID:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-choice-id element not found');
    }

    // Read prompt type from JSON block
    const promptTypeEl = document.getElementById('mcp-prompt-type');
    if (promptTypeEl) {
        try {
            window.mcpData.promptType = JSON.parse(promptTypeEl.textContent);
            debugLog('Bootstrap', 'Loaded promptType:', window.mcpData.promptType);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse prompt type:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-prompt-type element not found');
    }

    // Read JSON data blocks
    const defaultsEl = document.getElementById('mcp-defaults');
    if (defaultsEl) {
        try {
            window.mcpData.defaults = JSON.parse(defaultsEl.textContent);
            debugLog('Bootstrap', 'Loaded defaults:', window.mcpData.defaults);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse defaults:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-defaults element not found');
    }

    const optionsEl = document.getElementById('mcp-options');
    if (optionsEl) {
        try {
            window.mcpData.options = JSON.parse(optionsEl.textContent);
            debugLog('Bootstrap', 'Loaded options:', window.mcpData.options);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse options:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-options element not found');
    }

    const sessionStateEl = document.getElementById('mcp-session-state');
    if (sessionStateEl) {
        try {
            const parsed = JSON.parse(sessionStateEl.textContent || '{}');
            window.mcpData.sessionState = parsed && typeof parsed === 'object' ? parsed : {};
            debugLog('Bootstrap', 'Loaded sessionState:', window.mcpData.sessionState);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse session state:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-session-state element not found');
    }

    const i18nEl = document.getElementById('mcp-i18n');
    if (i18nEl) {
        try {
            window.mcpData.i18nTexts = JSON.parse(i18nEl.textContent || '{}');
            debugLog('Bootstrap', 'Loaded i18n texts, keys:', Object.keys(window.mcpData.i18nTexts).length);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse i18n texts:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-i18n element not found');
    }

    // Read prompt from JSON block
    const promptEl = document.getElementById('mcp-prompt');
    if (promptEl) {
        try {
            window.mcpData.prompt = JSON.parse(promptEl.textContent);
            debugLog('Bootstrap', 'Loaded prompt:', window.mcpData.prompt);
        } catch (e) {
            console.error('[Bootstrap] Failed to parse prompt:', e);
        }
    } else {
        console.warn('[Bootstrap] mcp-prompt element not found');
    }

    debugLog('Bootstrap', 'Data loading complete. mcpData:', window.mcpData);
})();

// Section: State Variables
// These are shared across modules
window.mcpState = {
    currentLang: window.mcpData.defaults.language || 'en',
    sessionState: window.mcpData.sessionState,
    placeholderVisible: window.mcpData.defaults.placeholder_visibility !== false,
    annotationEnabled: window.mcpData.defaults.annotation_enabled !== false,
    submitting: false,
    selectedIndices: new Set(),
    optionAnnotations: {},
    focusedIndex: -1,
    hasFinalResult: false,

    // Timeout state
    timeoutTimerId: null,
    timeoutTotal: 0,
    timeoutRemaining: 0,
    timeoutExpired: false,

    // WebSocket state
    ws: null,
    wsReconnectTimer: null,
    wsConnected: false,

    // Notification state
    notificationPermissionRequested: false,
    notifiedThreshold: false,
    notifiedTimeout: false,

    // Settings save timer
    saveSettingsTimer: null
};

// Initialize hasFinalResult based on session state
(function initState() {
    const state = window.mcpState;
    const sessionState = window.mcpData.sessionState;

    state.hasFinalResult = sessionState.status && sessionState.status !== 'pending';

    if (state.hasFinalResult && Array.isArray(sessionState.selected_indices)) {
        state.selectedIndices = new Set(sessionState.selected_indices);
    }
    if (sessionState.option_annotations) {
        state.optionAnnotations = sessionState.option_annotations;
    }
    if (typeof sessionState.additional_annotation === 'string') {
        const globalEl = document.getElementById('additionalAnnotation');
        if (globalEl) {
            globalEl.value = sessionState.additional_annotation || '';
        }
    }
})();
