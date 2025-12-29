/**
 * main.js - Application entry point
 * Initializes all modules and starts the application
 */

// Section: Application Init
(function initApp() {
    debugLog('Main', 'Starting application initialization...');

    const state = window.mcpState;
    const data = window.mcpData;

    // Validate required data is loaded
    if (!data.choiceId) {
        console.error('[Main] CRITICAL: choiceId not loaded!');
    }
    if (!data.options || data.options.length === 0) {
        console.warn('[Main] No options loaded');
    }
    if (!data.i18nTexts || Object.keys(data.i18nTexts).length === 0) {
        console.warn('[Main] No i18n texts loaded');
    }

    debugLog('Main', 'Data validation complete. Initializing modules...');

    // Initialize i18n first (applies language)
    if (typeof initializeI18n === 'function') {
        debugLog('Main', 'Initializing i18n...');
        initializeI18n();
    } else {
        console.warn('[Main] initializeI18n not found, applying language directly');
        applyLanguage(state.currentLang);
    }

    // Initialize config (UI settings, event handlers)
    if (typeof initializeConfig === 'function') {
        debugLog('Main', 'Initializing config...');
        initializeConfig();
    } else {
        console.error('[Main] initializeConfig not found!');
    }

    // Initialize rendering (options display)
    if (typeof initializeRender === 'function') {
        debugLog('Main', 'Initializing render...');
        initializeRender();
    } else {
        console.error('[Main] initializeRender not found!');
        // Fallback: try to call renderOptions directly
        if (typeof renderOptions === 'function') {
            debugLog('Main', 'Falling back to direct renderOptions call');
            renderOptions();
        }
    }

    // Initialize WebSocket (session sync)
    if (typeof initializeWebSocket === 'function') {
        debugLog('Main', 'Initializing WebSocket...');
        initializeWebSocket();
    } else {
        console.error('[Main] initializeWebSocket not found!');
        // Fallback
        if (typeof connectWebSocket === 'function') {
            debugLog('Main', 'Falling back to direct connectWebSocket call');
            connectWebSocket();
        }
    }

    // Initialize timeout countdown
    if (typeof initializeTimeout === 'function') {
        debugLog('Main', 'Initializing timeout...');
        initializeTimeout();
    } else {
        console.warn('[Main] initializeTimeout not found');
    }

    // Initialize interaction list
    if (typeof initializeInteractionList === 'function') {
        debugLog('Main', 'Initializing interaction list...');
        initializeInteractionList();
    } else {
        console.warn('[Main] initializeInteractionList not found');
    }

    // Initialize submission handlers
    if (typeof initializeSubmission === 'function') {
        debugLog('Main', 'Initializing submission...');
        initializeSubmission();
    }

    // Request notification permission
    if (typeof requestNotificationPermission === 'function') {
        requestNotificationPermission();
    }

    debugLog('Main', 'Application initialization complete!');
    console.log('[Main] Interactive Choice MCP Web Portal initialized');
})();
