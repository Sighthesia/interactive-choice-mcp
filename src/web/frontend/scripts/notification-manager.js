/**
 * notification-manager.js - Centralized notification management with focus tracking
 *
 * This module provides a NotificationManager class that handles all browser notifications
 * with real-time focus/visibility state tracking and flexible trigger modes.
 * 
 * Ref: Minidorcat - mcp-feedback-enhanced(https://github.com/Minidoracat/mcp-feedback-enhanced/blob/541ca1e5db8f5d1357d856f163feaacda1eb7144/src/mcp_feedback_enhanced/web/static/js/modules/notification/notification-manager.js)
 */

// Section: NotificationManager Class
class NotificationManager {
    constructor(options = {}) {
        // Configuration
        this.enabled = false;
        this.permission = 'default';
        this.triggerMode = 'tab_switch'; // Default trigger mode
        this.soundEnabled = true;
        this.customSoundPath = null;

        // State tracking
        this.lastSessionId = null; // Prevent duplicate notifications for same session
        this.isInitialized = false;
        this.hasFocus = document.hasFocus(); // Track window focus state

        // Storage keys
        this.STORAGE_KEY_ENABLED = 'notificationsEnabled';
        this.STORAGE_KEY_TRIGGER_MODE = 'notificationTriggerMode';

        // i18n function (can be overridden)
        this.t = options.t || ((key, defaultValue) => defaultValue || key);

        // Audio element for sounds
        this.audioElement = null;
    }

    // Section: Initialization
    initialize() {
        if (this.isInitialized) return;

        this.checkBrowserSupport();
        this.loadSettings();
        this.setupFocusTracking();
        this.isInitialized = true;

        console.log('[NotificationManager] Initialized', {
            enabled: this.enabled,
            permission: this.permission,
            triggerMode: this.triggerMode
        });
    }

    checkBrowserSupport() {
        if (!('Notification' in window)) {
            console.warn('[NotificationManager] Browser does not support notifications');
            return false;
        }
        return true;
    }

    // Section: Settings Management
    loadSettings() {
        // Load from window.mcpData (backend config) or localStorage
        const defaults = window.mcpData?.defaults || {};

        // Enable/disable notifications
        this.enabled = defaults.notify_new !== false;

        // Trigger mode from backend config
        const backendTriggerMode = defaults.notify_trigger_mode;
        if (backendTriggerMode && ['always', 'background', 'tab_switch', 'focus_lost'].includes(backendTriggerMode)) {
            this.triggerMode = backendTriggerMode;
        } else {
            // Fallback to localStorage
            const storedMode = localStorage.getItem(this.STORAGE_KEY_TRIGGER_MODE);
            if (storedMode && ['always', 'background', 'tab_switch', 'focus_lost'].includes(storedMode)) {
                this.triggerMode = storedMode;
            }
        }

        // Sound settings
        this.soundEnabled = defaults.notify_sound !== false;
        this.customSoundPath = defaults.notify_sound_path || null;

        // Permission status
        this.permission = Notification.permission;
    }

    setEnabled(enabled) {
        this.enabled = enabled;
        try {
            localStorage.setItem(this.STORAGE_KEY_ENABLED, enabled);
            console.log('[NotificationManager] Notifications', enabled ? 'enabled' : 'disabled');
        } catch (error) {
            console.error('[NotificationManager] Failed to save enabled state:', error);
        }
    }

    setTriggerMode(mode) {
        const validModes = ['always', 'background', 'tab_switch', 'focus_lost'];
        if (!validModes.includes(mode)) {
            console.error('[NotificationManager] Invalid trigger mode:', mode);
            return;
        }

        this.triggerMode = mode;
        try {
            localStorage.setItem(this.STORAGE_KEY_TRIGGER_MODE, mode);
            console.log('[NotificationManager] Trigger mode updated:', mode);
        } catch (error) {
            console.error('[NotificationManager] Failed to save trigger mode:', error);
        }
    }

    // Section: Focus Tracking
    setupFocusTracking() {
        const self = this;

        // Track window focus events
        window.addEventListener('focus', function () {
            self.hasFocus = true;
            console.log('[NotificationManager] Window gained focus');
        });

        window.addEventListener('blur', function () {
            self.hasFocus = false;
            console.log('[NotificationManager] Window lost focus');
        });
    }

    // Section: Notification Logic
    canNotify() {
        if (!this.checkBrowserSupport()) {
            return false;
        }

        if (!this.enabled) {
            return false;
        }

        if (this.permission !== 'granted') {
            return false;
        }

        // Check trigger mode conditions
        switch (this.triggerMode) {
            case 'always':
                return true;
            case 'tab_switch':
                // Only notify when interaction page loses focus (tab is switched away)
                // This is for users who want notifications only when switching within the browser
                return document.hidden;
            case 'background':
                // Notify when browser window loses focus (switched to another app)
                // This includes scenarios like switching to another application
                return !this.hasFocus && !document.hidden;
            case 'focus_lost':
                // Notify when interaction page loses focus OR browser window loses focus
                // This covers both tab switching and switching to other apps
                return document.hidden || !this.hasFocus;
            default:
                return false;
        }
    }

    async requestPermission() {
        if (!this.checkBrowserSupport()) {
            console.warn('[NotificationManager] Cannot request permission - not supported');
            return false;
        }

        if (this.permission === 'granted') {
            return true;
        }

        try {
            const permission = await Notification.requestPermission();
            this.permission = permission;
            console.log('[NotificationManager] Permission result:', permission);
            return permission === 'granted';
        } catch (error) {
            console.error('[NotificationManager] Permission request failed:', error);
            return false;
        }
    }

    playSound() {
        if (!this.soundEnabled) return;

        try {
            const soundPath = this.customSoundPath || '/static/sounds/notification.mp3';

            // Reuse or create audio element
            if (!this.audioElement) {
                this.audioElement = new Audio();
            }

            // Only update source if different
            if (this.audioElement.src !== soundPath && !this.audioElement.src.endsWith(soundPath)) {
                this.audioElement.src = soundPath;
            }

            // Reset and play
            this.audioElement.currentTime = 0;
            this.audioElement.volume = 0.5;
            this.audioElement.play().catch(e => {
                // Autoplay may be blocked by browser policy
                console.debug('[NotificationManager] Sound playback blocked:', e.message);
            });
        } catch (error) {
            console.warn('[NotificationManager] Failed to play sound:', error);
        }
    }

    showNotification(title, body, options = {}) {
        if (!this.canNotify()) {
            console.log('[NotificationManager] Notification skipped - conditions not met', {
                enabled: this.enabled,
                permission: this.permission,
                pageHidden: document.hidden,
                hasFocus: this.hasFocus,
                triggerMode: this.triggerMode
            });
            return;
        }

        try {
            const notification = new Notification(title, {
                body,
                icon: options.icon || '/static/icon-192.png',
                badge: options.badge || '/static/icon-192.png',
                tag: options.tag || 'mcp-notification',
                timestamp: Date.now(),
                silent: options.silent || false,
                ...options
            });

            // Play sound
            this.playSound();

            // Handle click
            if (options.onClick) {
                notification.onclick = options.onClick;
            } else {
                notification.onclick = () => {
                    window.focus();
                    notification.close();
                    console.log('[NotificationManager] Notification clicked, window focused');
                };
            }

            // Auto-close after delay
            const autoCloseDelay = options.autoClose || 5000;
            if (autoCloseDelay > 0) {
                setTimeout(() => notification.close(), autoCloseDelay);
            }

            console.log('[NotificationManager] Notification sent', { title, body });
            return notification;
        } catch (error) {
            console.error('[NotificationManager] Failed to show notification:', error);
            return null;
        }
    }

    // Section: Session Notification
    notifyNewSession(sessionId, projectPath = '') {
        // Prevent duplicate notifications for the same session
        if (sessionId === this.lastSessionId) {
            console.log('[NotificationManager] Skipping duplicate session notification');
            return;
        }

        if (!this.canNotify()) {
            return;
        }

        this.lastSessionId = sessionId;

        const truncatedPath = this.truncatePath(projectPath);
        const title = this.t('notification.session.title', 'MCP Choice - New Session');
        const body = `${this.t('notification.session.ready', 'Ready')}: ${truncatedPath}`;

        this.showNotification(title, body, {
            tag: 'mcp-session',
            autoClose: 5000
        });
    }

    // Section: Timeout Notifications
    notifyUpcoming(secondsRemaining, timeoutTotal) {
        if (!this.canNotify()) {
            return;
        }

        const title = this.t('notification.timeout.upcomingTitle', 'Timeout Approaching');
        const body = this.t('notification.timeout.upcomingBody', `Timeout in ${secondsRemaining} seconds`);

        this.showNotification(title, body, {
            tag: 'mcp-timeout-upcoming',
            autoClose: 5000
        });
    }

    notifyTimeout(timeoutAction) {
        if (!this.canNotify()) {
            return;
        }

        let title, body;

        if (timeoutAction === 'submit') {
            title = this.t('notification.timeout.submittedTitle', 'Auto Submitted');
            body = this.t('notification.timeout.submittedBody', 'Your selection was automatically submitted due to timeout');
        } else if (timeoutAction === 'cancel') {
            title = this.t('notification.timeout.cancelledTitle', 'Timeout Cancelled');
            body = this.t('notification.timeout.cancelledBody', 'The interaction was cancelled due to timeout');
        } else {
            title = this.t('notification.timeout.reachedTitle', 'Timeout Reached');
            body = this.t('notification.timeout.reachedBody', 'The interaction has timed out');
        }

        this.showNotification(title, body, {
            tag: 'mcp-timeout-reached',
            autoClose: 5000
        });
    }

    // Section: Utilities
    truncatePath(path, maxLength = 50) {
        if (!path) return '';
        if (path.length <= maxLength) return path;
        return path.substring(0, maxLength - 3) + '...';
    }

    resetSessionTracking() {
        this.lastSessionId = null;
    }
}

// Section: Global Instance
let notificationManagerInstance = null;

function getNotificationManager() {
    if (!notificationManagerInstance) {
        notificationManagerInstance = new NotificationManager();
        notificationManagerInstance.initialize();
    }
    return notificationManagerInstance;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NotificationManager, getNotificationManager };
}
