/**
 * websocket.js - WebSocket connection management
 * Handles session sync, status updates, and connection state
 */

// Section: Connection Status
function updateConnectionStatus(text, stateClass = '') {
    const headerStatusText = document.getElementById('statusText');
    const headerStatusDot = document.getElementById('connectionDot');
    if (headerStatusText) headerStatusText.innerText = text;
    if (headerStatusDot) {
        headerStatusDot.className = 'status-dot' + (stateClass ? ' ' + stateClass : '');
    }
}

// Section: WebSocket Connection
function connectWebSocket() {
    const state = window.mcpState;
    const choiceId = window.mcpData.choiceId;

    if (!choiceId) {
        console.error('[WebSocket] Cannot connect: choiceId is null/undefined');
        updateConnectionStatus(t('status.error'), 'offline');
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = protocol + '://' + window.location.host + '/ws/' + choiceId;
    debugLog('WebSocket', 'Connecting to:', wsUrl);

    if (state.ws) {
        state.ws.close();
    }

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        state.wsConnected = true;
        updateConnectionStatus(t('status.connected'), '');
        if (state.wsReconnectTimer) {
            clearTimeout(state.wsReconnectTimer);
            state.wsReconnectTimer = null;
        }
    };

    state.ws.onclose = () => {
        state.wsConnected = false;
        if (state.hasFinalResult) {
            // Session completed, connection closed is expected
            // Show green "Completed" - use 'success' class for green dot
            updateConnectionStatus(t('status.completed'), 'success');
            return;
        }
        updateConnectionStatus(t('status.offline'), 'offline');
        if (!state.submitting) {
            state.wsReconnectTimer = setTimeout(connectWebSocket, 1500);
        }
    };

    state.ws.onmessage = (event) => {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch (e) {
            return;
        }

        if (data.type === 'sync') {
            updateTimeoutFromServer(data.remaining_seconds, data.timeout_seconds);
        }

        if (data.type === 'status') {
            const serverIndices = Array.isArray(data.selected_indices) ? data.selected_indices : null;
            const serverAnnotations = data.option_annotations || null;
            const serveradditionalAnnotation = typeof data.additional_annotation === 'string' ? data.additional_annotation : null;

            if (typeof data.remaining_seconds === 'number') {
                updateTimeoutFromServer(data.remaining_seconds, data.timeout_seconds);
            }

            if (data.status === 'timeout') {
                applyFinalizedState({
                    action_status: data.action_status || 'timeout',
                    selected_indices: serverIndices || Array.from(state.selectedIndices),
                    option_annotations: serverAnnotations || state.optionAnnotations,
                    additional_annotation: serveradditionalAnnotation ?? (document.getElementById('additionalAnnotation')?.value || null)
                });
            } else if (data.status === 'submitted') {
                applyFinalizedState({
                    action_status: data.action_status || 'selected',
                    selected_indices: serverIndices || Array.from(state.selectedIndices),
                    option_annotations: serverAnnotations || state.optionAnnotations,
                    additional_annotation: serveradditionalAnnotation ?? (document.getElementById('additionalAnnotation')?.value || null)
                });
            } else if (data.status === 'cancelled') {
                applyFinalizedState({
                    action_status: 'cancelled',
                    selected_indices: serverIndices || [],
                    option_annotations: serverAnnotations || state.optionAnnotations,
                    additional_annotation: serveradditionalAnnotation ?? (document.getElementById('additionalAnnotation')?.value || null)
                });
            } else if (data.status === 'connected') {
                updateConnectionStatus('Connected', '');
            }
        }
    };
}

function sendUpdateTimeout(seconds) {
    const state = window.mcpState;
    if (!state.wsConnected || !state.ws) return;
    state.ws.send(JSON.stringify({ type: 'update_timeout', seconds }));
}

// Section: Finalized State
function applyFinalizedState(stateData) {
    debugLog('WebSocket', 'Applying finalized state:', stateData.action_status);
    const state = window.mcpState;
    state.sessionState = Object.assign({}, state.sessionState || {}, stateData || {});
    state.hasFinalResult = true;
    state.submitting = false;
    stopTimeout();

    const statusEl = document.getElementById('status');
    const actionKey = stateData.action_status || 'manual';
    const statusMap = getStatusMap();
    const config = statusMap[actionKey] || statusMap['manual'];

    if (Array.isArray(stateData.selected_indices)) {
        state.selectedIndices = new Set(stateData.selected_indices);
        renderOptions();
    }
    if (stateData.option_annotations) {
        state.optionAnnotations = stateData.option_annotations;
    }
    if (typeof stateData.additional_annotation === 'string') {
        const globalEl = document.getElementById('additionalAnnotation');
        if (globalEl) {
            globalEl.value = stateData.additional_annotation || '';
        }
    }

    if (statusEl) {
        statusEl.className = 'status ' + config.class;
        statusEl.innerText = config.text;
        statusEl.style.display = 'block';
        setTimeout(() => {
            statusEl.style.opacity = '1';
        }, 10);
    }
    setTimeout(() => {
        document.body.classList.add('submitted');
    }, 10);

    // Update header status based on session state
    if (actionKey === 'interrupted') {
        // Interrupted session - show red "Interrupted"
        updateConnectionStatus(t('status.interrupted'), 'error');
    } else {
        // Completed session - show green "Completed"
        updateConnectionStatus(t('status.completed'), 'success');
    }

    const submitBtn = document.getElementById('submitBatchBtn');
    const cancelBtn = document.getElementById('cancelButton');
    if (submitBtn) submitBtn.disabled = true;
    if (cancelBtn) cancelBtn.disabled = true;

    // Show finalized progress bar animation with state-specific colors
    const bar = document.getElementById('timeoutProgressBar');
    const container = document.getElementById('timeoutContainer');
    const timeoutText = document.getElementById('timeoutText');
    if (bar && container) {
        bar.classList.remove('success', 'warning', 'danger');
        bar.style.width = '100%';
        container.style.display = 'block';

        if (actionKey.startsWith('timeout')) {
            bar.classList.add('warning');
            if (timeoutText) timeoutText.innerText = t('status.timeout');
        } else if (actionKey === 'interrupted') {
            bar.classList.add('danger');
            if (timeoutText) timeoutText.innerText = t('status.interrupted');
        } else {
            bar.classList.add('success');
            if (timeoutText) timeoutText.innerText = t('status.completed');
        }
    }

    // Trigger interaction list refresh to update current item's status
    debugLog('WebSocket', 'Triggering interaction list refresh...');
    if (typeof fetchInteractionListFallback === 'function') {
        fetchInteractionListFallback();
    }
}

// Section: WebSocket Reconnection (for in-page navigation)
function reconnectWebSocket(newSessionId) {
    debugLog('WebSocket', 'Reconnecting for session:', newSessionId);
    const state = window.mcpState;

    // Clear any pending reconnect timer
    if (state.wsReconnectTimer) {
        clearTimeout(state.wsReconnectTimer);
        state.wsReconnectTimer = null;
    }

    // Close existing connection
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }

    // Reset state for new session
    state.wsConnected = false;
    state.hasFinalResult = false;
    state.submitting = false;

    // Connect to new session
    connectWebSocket();
}

function disconnectWebSocket() {
    debugLog('WebSocket', 'Disconnecting WebSocket for persisted session');
    const state = window.mcpState;

    // Clear any pending reconnect timer
    if (state.wsReconnectTimer) {
        clearTimeout(state.wsReconnectTimer);
        state.wsReconnectTimer = null;
    }

    // Close existing connection
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }

    state.wsConnected = false;
    // For persisted sessions, show green "Completed"
    updateConnectionStatus(t('status.completed'), 'success');
}

// Section: Initialize WebSocket
function initializeWebSocket() {
    debugLog('WebSocket', 'Initializing...');
    debugLog('WebSocket', 'choiceId:', window.mcpData.choiceId);
    connectWebSocket();
}
