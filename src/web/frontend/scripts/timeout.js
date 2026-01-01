/**
 * timeout.js - Timeout countdown and notification handling
 */

// Section: Notifications (Legacy - Replaced by NotificationManager)
// These functions are kept for backward compatibility but delegate to NotificationManager
function requestNotificationPermission() {
    const manager = getNotificationManager();
    if (manager) {
        manager.requestPermission();
    }

    // Warm up Web Audio API on user interaction
    warmUpWebAudio();
}

/**
 * Warm up Web Audio API by creating a silent context
 * This is required by browsers to allow audio playback without user interaction
 */
function warmUpWebAudio() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;

        // Create a temporary context and resume it to unlock audio
        const tempContext = new AudioContext();
        if (tempContext.state === 'suspended') {
            tempContext.resume().then(() => {
                console.debug('[Web Audio] AudioContext resumed');
                tempContext.close();
            }).catch(err => {
                console.debug('[Web Audio] Failed to resume AudioContext:', err);
            });
        } else {
            tempContext.close();
        }
    } catch (error) {
        console.debug('[Web Audio] Warm-up failed:', error);
    }
}

function playNotificationSound() {
    const manager = getNotificationManager();
    if (manager) {
        manager.playSound();
    }
}

function notifyEvent(title, body) {
    const manager = getNotificationManager();
    if (manager) {
        manager.showNotification(title, body);
    }
}

/**
 * Test notification sound playback
 */
function testNotificationSound() {
    const manager = getNotificationManager();
    if (manager) {
        manager.playSound();
    }
}

// Section: Timeout Management
function stopTimeout() {
    const state = window.mcpState;
    if (state.timeoutTimerId !== null) {
        clearInterval(state.timeoutTimerId);
        state.timeoutTimerId = null;
    }
}

function renderTimeout() {
    const state = window.mcpState;
    const timeoutText = document.getElementById('timeoutText');
    const container = document.getElementById('timeoutContainer');
    const bar = document.getElementById('timeoutProgressBar');

    if (!state.timeoutTotal || state.timeoutTotal <= 0) {
        if (timeoutText) timeoutText.innerText = 'No Timeout';
        if (container) container.style.display = 'none';
        if (bar) {
            bar.style.width = '0%';
            bar.classList.remove('warning', 'danger');
        }
        return;
    }

    if (container) container.style.display = 'block';
    const clamped = Math.max(0, state.timeoutRemaining);
    const mins = Math.floor(clamped / 60);
    const secs = clamped % 60;
    if (timeoutText) timeoutText.innerText = mins + ':' + (secs < 10 ? '0' : '') + secs;

    const percentage = Math.max(0, (state.timeoutRemaining / state.timeoutTotal) * 100);
    if (bar) {
        bar.style.width = percentage + '%';
        bar.classList.toggle('warning', percentage < 50 && percentage >= 20);
        bar.classList.toggle('danger', percentage < 20);
    }

    // Use upcoming_threshold from config, default to 60 seconds
    const upcomingThreshold = window.mcpData.defaults?.upcoming_threshold || 60;
    const shouldNotifyUpcoming = window.mcpData.defaults?.notify_upcoming !== false;

    // Check if already notified for this session using sessionStorage
    const sessionId = window.mcpData.choiceId;
    const notifiedKey = 'mcp_notified_threshold_' + sessionId;
    const alreadyNotified = state.notifiedThreshold || sessionStorage.getItem(notifiedKey) === 'true';

    if (shouldNotifyUpcoming && state.timeoutRemaining <= upcomingThreshold && state.timeoutRemaining > 0 && !alreadyNotified) {
        // Use NotificationManager for focus-aware notifications
        const manager = getNotificationManager();
        if (manager && manager.canNotify()) {
            manager.notifyUpcoming(state.timeoutRemaining, state.timeoutTotal);
            state.notifiedThreshold = true;
            sessionStorage.setItem(notifiedKey, 'true');
        }
    }

    if (state.timeoutRemaining <= 0 && !state.timeoutExpired) {
        state.timeoutExpired = true;
        handleTimeoutReached();
    }
}

function startTick() {
    const state = window.mcpState;
    // Stop existing timer if any, to ensure accurate synchronization with server time
    if (state.timeoutTimerId !== null) {
        clearInterval(state.timeoutTimerId);
        state.timeoutTimerId = null;
    }
    state.timeoutTimerId = setInterval(() => {
        if (state.submitting) {
            stopTimeout();
            return;
        }
        state.timeoutRemaining = Math.max(0, state.timeoutRemaining - 1);
        renderTimeout();
    }, 1000);
}

function startTimeout(seconds) {
    const state = window.mcpState;
    stopTimeout();
    if (state.hasFinalResult) {
        state.timeoutTotal = 0;
        state.timeoutRemaining = 0;
        renderTimeout();
        return;
    }
    state.notifiedThreshold = false;
    state.notifiedTimeout = false;
    state.timeoutExpired = false;
    const sec = Number.isFinite(Number(seconds)) ? parseInt(seconds, 10) : 0;
    state.timeoutTotal = sec > 0 ? sec : 0;
    state.timeoutRemaining = state.timeoutTotal;
    renderTimeout();
    if (state.timeoutTotal > 0) {
        startTick();
    }
}

function updateTimeoutFromServer(remainingSeconds, totalSeconds) {
    const state = window.mcpState;
    if (state.hasFinalResult) return;
    if (!Number.isFinite(Number(remainingSeconds))) return;
    const remaining = Math.max(0, Math.round(Number(remainingSeconds)));
    const total = Number.isFinite(Number(totalSeconds)) && totalSeconds > 0 ? Math.round(Number(totalSeconds)) : null;
    if (total) {
        state.timeoutTotal = total;
    } else if (state.timeoutTotal < remaining) {
        state.timeoutTotal = remaining;
    }
    state.timeoutRemaining = remaining;
    if (remaining > 0) {
        state.timeoutExpired = false;
        state.notifiedTimeout = false;
    }
    renderTimeout();
    // Sync interaction list with updated timeout
    if (typeof renderInteractionList === 'function') {
        renderInteractionList();
    }
    if (state.timeoutTotal > 0) {
        startTick();
    }
}

function handleTimeoutReached() {
    const state = window.mcpState;
    stopTimeout();
    // Note: Don't update connection status here - timeout is a session state, not connection state
    // The status element will show the timeout state
    const config = collectConfig();
    if (config.timeout_action === 'reinvoke') {
        submitPayload({ action_status: 'timeout_reinvoke_requested' }, 'timeout');
    } else if (config.timeout_action === 'cancel') {
        submitPayload({ action_status: 'timeout_cancelled' }, 'timeout');
    } else {
        if (state.selectedIndices.size > 0) {
            submitBatch('timeout_auto_submitted');
        } else {
            const defaults = window.mcpData.defaults;
            const useRecommended = isUseDefaultOption();
            if (useRecommended) {
                // Apply recommended options selection and submit
                applyDefaultSelections();
                submitBatch('timeout_auto_submitted');
            } else {
                submitPayload({ action_status: 'timeout_cancelled' }, 'timeout_cancelled');
            }
        }
    }
    // Check if already notified timeout for this session
    const sessionId = window.mcpData.choiceId;
    const timeoutNotifiedKey = 'mcp_notified_timeout_' + sessionId;
    if (!state.notifiedTimeout && sessionStorage.getItem(timeoutNotifiedKey) !== 'true') {
        // Use NotificationManager for focus-aware notifications
        const manager = getNotificationManager();
        if (manager && manager.canNotify()) {
            manager.notifyTimeout(config.timeout_action);
            state.notifiedTimeout = true;
            sessionStorage.setItem(timeoutNotifiedKey, 'true');
        }
    }
}

// Section: Initialize Timeout
function initializeTimeout() {
    debugLog('Timeout', 'Initializing...');

    // Initialize NotificationManager and request permission
    const manager = getNotificationManager();
    if (manager) {
        manager.requestPermission();
    }

    // Check sessionStorage for previous notification state
    const sessionId = window.mcpData.choiceId;
    if (sessionId) {
        const notifiedKey = 'mcp_notified_threshold_' + sessionId;
        const timeoutNotifiedKey = 'mcp_notified_timeout_' + sessionId;
        if (sessionStorage.getItem(notifiedKey) === 'true') {
            window.mcpState.notifiedThreshold = true;
        }
        if (sessionStorage.getItem(timeoutNotifiedKey) === 'true') {
            window.mcpState.notifiedTimeout = true;
        }
    }

    // Start timeout with initial value from defaults
    // This ensures timeout is displayed immediately, even before WebSocket connects
    const state = window.mcpState;
    const defaults = window.mcpData.defaults;
    if (!state.hasFinalResult && defaults && typeof defaults.timeout_seconds === 'number' && defaults.timeout_seconds > 0) {
        debugLog('Timeout', 'Starting initial timeout:', defaults.timeout_seconds, 'seconds');
        state.timeoutTotal = defaults.timeout_seconds;
        state.timeoutRemaining = defaults.timeout_seconds;
        renderTimeout();
        startTick();
    }

    document.addEventListener('visibilitychange', () => {
        // Don't reset notification state on visibility change - 
        // notifications should only trigger once per session
    });
}
