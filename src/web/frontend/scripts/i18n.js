/**
 * i18n.js - Internationalization helpers
 * Provides t() function and UI text update utilities
 */

// Section: Translation Helper
/**
 * Get translated text for the given key
 * @param {string} key - The i18n key to look up
 * @returns {string} The translated text or the key if not found
 */
function t(key) {
    const entry = window.mcpData.i18nTexts[key];
    if (entry && typeof entry === 'object') {
        return entry[window.mcpState.currentLang] || entry['en'] || key;
    }
    return key;
}

// Section: Language Application
/**
 * Apply a language setting and update the UI
 * @param {string} lang - Language code ('en' or 'zh')
 */
function applyLanguage(lang) {
    window.mcpState.currentLang = lang;
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) languageSelect.value = lang;
    localStorage.setItem('mcp-language', lang);
    updateUITexts();
}

// Section: UI Text Updates
/**
 * Update all UI elements with data-i18n attributes
 */
function updateUITexts() {
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const text = t(key);
        if (text !== key) {
            const tagName = el.tagName.toLowerCase();
            if (tagName === 'option') {
                el.textContent = text;
            } else if (tagName === 'input' && el.type === 'text') {
                el.placeholder = text;
            } else if (el.querySelector('select, input')) {
                const childNodes = Array.from(el.childNodes);
                const textNode = childNodes.find(n => n.nodeType === Node.TEXT_NODE);
                if (textNode) {
                    textNode.textContent = text + ' ';
                }
            } else {
                el.textContent = text;
            }
        }
    });

    // Update annotation placeholder
    const globalAnnotation = document.getElementById('globalAnnotation');
    if (globalAnnotation) globalAnnotation.placeholder = t('terminal.global_annotation_prompt');

    // Update interaction loading text
    const interactionEmpty = document.querySelector('.interaction-empty');
    if (interactionEmpty && interactionEmpty.textContent.includes('Loading')) {
        interactionEmpty.textContent = t('list.loading');
    }

    // Update status text based on connection state
    // Note: CSS classes are: (none)=in-progress, success=completed, error=interrupted, offline=offline
    const statusText = document.getElementById('statusText');
    const connectionDot = document.getElementById('connectionDot');
    if (statusText && connectionDot) {
        if (connectionDot.classList.contains('success')) {
            statusText.textContent = t('status.session_completed');
        } else if (connectionDot.classList.contains('error')) {
            statusText.textContent = t('status.interrupted');
        } else if (connectionDot.classList.contains('offline')) {
            statusText.textContent = t('status.offline');
        } else {
            // Default (no special class) = in progress
            statusText.textContent = t('status.connected');
        }
    }

    // Keep button labels in sync with current language & mode
    if (typeof updateSubmitBtn === 'function') {
        updateSubmitBtn();
    }
}

// Section: Status Map
/**
 * Get the status map for display messages
 * Note: This needs to be called after t() is available
 */
function getStatusMap() {
    return {
        'manual': { text: t('status_message.manual'), class: 'manual' },
        'selected': { text: t('status_message.manual'), class: 'success' },
        'timeout_auto_submitted': { text: t('status_message.timeout_auto_submitted'), class: 'auto_submitted' },
        'timeout_cancelled': { text: t('status_message.timeout_cancelled'), class: 'timeout' },
        'timeout_reinvoke_requested': { text: t('status_message.timeout_reinvoke_requested'), class: 'timeout' },
        'cancelled': { text: t('status_message.cancelled'), class: 'cancelled' },
        'cancel_with_annotation': { text: t('status_message.cancel_with_annotation'), class: 'cancelled' },
        'interrupted': { text: t('status_message.interrupted'), class: 'interrupted' },
        'error': { text: t('status_message.server_error'), class: 'error' }
    };
}

// Section: Initialize I18n
function initializeI18n() {
    debugLog('I18n', 'Initializing...');
    const state = window.mcpState;

    // Apply the current language
    applyLanguage(state.currentLang);
    debugLog('I18n', 'Applied language:', state.currentLang);
}
