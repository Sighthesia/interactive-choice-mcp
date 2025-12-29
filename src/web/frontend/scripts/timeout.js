/**
 * timeout.js - Timeout countdown and notification handling
 */

// Section: Notifications
function requestNotificationPermission() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') return;
    try {
        Notification.requestPermission();
    } catch (e) {
        console.warn('[Notification] Permission request failed:', e);
    }
}

function notifyEvent(title, body) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    try {
        new Notification(title, { body });
    } catch (e) {
        console.warn('[Notification] Failed to show notification:', e);
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

    if (state.timeoutRemaining <= 10 && state.timeoutRemaining > 0 && document.hidden && !state.notifiedThreshold) {
        requestNotificationPermission();
        notifyEvent('Timeout approaching', '~' + state.timeoutRemaining + 's remaining');
        state.notifiedThreshold = true;
    }

    if (state.timeoutRemaining <= 0 && !state.timeoutExpired) {
        state.timeoutExpired = true;
        handleTimeoutReached();
    }
}

function startTick() {
    const state = window.mcpState;
    if (state.timeoutTimerId !== null) return;
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
    if (state.timeoutTotal > 0) {
        startTick();
    }
}

function handleTimeoutReached() {
    const state = window.mcpState;
    stopTimeout();
    updateConnectionStatus('Timeout', 'offline');
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
            const hasDefault = defaults.timeout_default_enabled && defaults.timeout_default_index !== null;
            if (hasDefault) {
                submitPayload({ action_status: 'timeout_auto_submitted' }, 'timeout_auto_submitted');
            } else {
                submitPayload({ action_status: 'timeout_cancelled' }, 'timeout_cancelled');
            }
        }
    }
    if (!state.notifiedTimeout) {
        requestNotificationPermission();
        notifyEvent('Interaction timed out', 'The choice session has expired.');
        state.notifiedTimeout = true;
    }
}

// Section: Initialize Timeout
function initializeTimeout() {
    debugLog('Timeout', 'Initializing...');
    requestNotificationPermission();

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            window.mcpState.notifiedThreshold = false;
        }
    });
}
