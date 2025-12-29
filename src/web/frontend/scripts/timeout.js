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

// Audio element for notification sounds
let notificationAudio = null;

function playNotificationSound() {
    const defaults = window.mcpData.defaults || {};

    // Check if sound is enabled
    if (defaults.notify_sound === false) return;

    try {
        // Use custom sound path if provided, otherwise use default
        const soundPath = defaults.notify_sound_path || '/static/sounds/notification.mp3';

        // Reuse or create audio element
        if (!notificationAudio) {
            notificationAudio = new Audio();
        }

        // Only update source if different
        if (notificationAudio.src !== soundPath && !notificationAudio.src.endsWith(soundPath)) {
            notificationAudio.src = soundPath;
        }

        // Reset and play
        notificationAudio.currentTime = 0;
        notificationAudio.volume = 0.5;
        notificationAudio.play().catch(e => {
            // Autoplay may be blocked by browser policy
            console.debug('[Notification] Sound playback blocked:', e.message);
        });
    } catch (e) {
        console.warn('[Notification] Failed to play sound:', e);
    }
}

function notifyEvent(title, body) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;

    try {
        new Notification(title, { body });
        // Play sound with notification
        playNotificationSound();
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

    // Use upcoming_threshold from config, default to 60 seconds
    const upcomingThreshold = window.mcpData.defaults?.upcoming_threshold || 60;
    const shouldNotifyUpcoming = window.mcpData.defaults?.notify_upcoming !== false;

    // Check if already notified for this session using sessionStorage
    const sessionId = window.mcpData.choiceId;
    const notifiedKey = 'mcp_notified_threshold_' + sessionId;
    const alreadyNotified = state.notifiedThreshold || sessionStorage.getItem(notifiedKey) === 'true';

    if (shouldNotifyUpcoming && state.timeoutRemaining <= upcomingThreshold && state.timeoutRemaining > 0 && !alreadyNotified) {
        // Only notify if page is hidden or notify_if_focused is enabled
        const notifyIfFocused = window.mcpData.defaults?.notify_if_focused !== false;
        if (document.hidden || notifyIfFocused) {
            requestNotificationPermission();
            notifyEvent('Timeout approaching', '~' + state.timeoutRemaining + 's remaining');
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
            const hasDefault = defaults.timeout_default_enabled && defaults.timeout_default_index !== null;
            if (hasDefault) {
                submitPayload({ action_status: 'timeout_auto_submitted' }, 'timeout_auto_submitted');
            } else {
                submitPayload({ action_status: 'timeout_cancelled' }, 'timeout_cancelled');
            }
        }
    }
    // Check if already notified timeout for this session
    const sessionId = window.mcpData.choiceId;
    const timeoutNotifiedKey = 'mcp_notified_timeout_' + sessionId;
    if (!state.notifiedTimeout && sessionStorage.getItem(timeoutNotifiedKey) !== 'true') {
        requestNotificationPermission();
        notifyEvent('Interaction timed out', 'The choice session has expired.');
        state.notifiedTimeout = true;
        sessionStorage.setItem(timeoutNotifiedKey, 'true');
    }
}

// Section: Initialize Timeout
function initializeTimeout() {
    debugLog('Timeout', 'Initializing...');
    requestNotificationPermission();

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

    document.addEventListener('visibilitychange', () => {
        // Don't reset notification state on visibility change - 
        // notifications should only trigger once per session
    });
}
