/**
 * submission.js - Form submission and API communication
 * Handles batch submit, cancel, and payload building
 */

// Section: Submission
async function postSelection(payload, statusType = 'manual') {
    const state = window.mcpState;
    const choiceId = window.mcpData.choiceId;

    if (state.hasFinalResult) {
        applyFinalizedState(state.sessionState.status ? state.sessionState : payload);
        return;
    }
    if (state.submitting) return;
    state.submitting = true;

    const statusEl = document.getElementById('status');
    const headerStatusText = document.getElementById('statusText');
    const headerStatusDot = document.getElementById('connectionDot');

    if (headerStatusText) headerStatusText.innerText = t('status.submitting');
    if (headerStatusDot) headerStatusDot.className = 'status-dot busy';

    try {
        const res = await fetch('/choice/' + choiceId + '/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        let data = null;
        try {
            data = await res.json();
        } catch (e) {
            data = null;
        }
        if (!res.ok) {
            let errorDetail = 'Submission failed';
            if (data && data.detail) {
                errorDetail = data.detail;
            } else {
                const text = await res.text().catch(() => '');
                if (text) errorDetail = text.substring(0, 200);
            }
            if (statusEl) {
                statusEl.className = 'status error';
                statusEl.innerText = t('status_message.server_error') + ' (' + res.status + '): ' + errorDetail;
                statusEl.style.display = 'block';
            }
            if (headerStatusText) headerStatusText.innerText = t('status.error');
            if (headerStatusDot) headerStatusDot.className = 'status-dot offline';
            state.submitting = false;
            return;
        }

        const actionKey = payload.action_status || statusType || 'manual';
        if (data && data.status === 'already-set') {
            if (data.state) {
                applyFinalizedState(data.state);
                return;
            }
            applyFinalizedState({ action_status: actionKey });
            return;
        }

        applyFinalizedState({
            action_status: actionKey,
            selected_indices: payload.selected_indices || Array.from(state.selectedIndices),
            option_annotations: payload.option_annotations || state.optionAnnotations,
            global_annotation: payload.global_annotation || document.getElementById('globalAnnotation')?.value || null
        });
    } catch (e) {
        if (statusEl) {
            statusEl.className = 'status error';
            statusEl.innerText = 'Network error. Please try again.';
            statusEl.style.display = 'block';
        }
        if (headerStatusText) headerStatusText.innerText = t('status.offline');
        if (headerStatusDot) headerStatusDot.className = 'status-dot offline';
        state.submitting = false;
    }
}

function submitBatch(statusType = 'manual') {
    const state = window.mcpState;
    const payload = {
        action_status: 'selected',
        selected_indices: Array.from(state.selectedIndices),
    };
    if (isAnnotationEnabled()) {
        payload.option_annotations = state.optionAnnotations;
        payload.global_annotation = document.getElementById('globalAnnotation')?.value || null;
    }
    submitPayload(payload, statusType);
}

function submitCancel() {
    const state = window.mcpState;
    const payload = { action_status: hasAnnotations() ? 'cancel_with_annotation' : 'cancelled' };
    if (hasAnnotations()) {
        payload.option_annotations = state.optionAnnotations;
        payload.global_annotation = document.getElementById('globalAnnotation')?.value || null;
    }
    submitPayload(payload, payload.action_status);
}

function submitPayload(base, statusType = 'manual') {
    const state = window.mcpState;
    if (state.hasFinalResult) {
        applyFinalizedState(state.sessionState.status ? state.sessionState : base);
        return;
    }
    if (!state.wsConnected) {
        const statusEl = document.getElementById('status');
        if (statusEl) {
            statusEl.className = 'status error';
            statusEl.innerText = t('status_message.sever_offline');
            statusEl.style.display = 'block';
        }
        updateConnectionStatus(t('status.offline'), 'offline');
        return;
    }
    const config = collectConfig();
    base.config = config;
    postSelection(base, statusType);
}

// Section: Initialize Submission
function initializeSubmission() {
    // Button click handlers are set up by render.js via onclick attributes in HTML
    // This function is here for consistency and potential future initialization
}
