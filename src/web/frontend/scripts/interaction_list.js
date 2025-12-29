/**
 * interaction_list.js - Interaction list sidebar management
 * Handles WebSocket updates, filtering, and rendering of interaction list
 */

// Section: State
let interactionListWs = null;
let interactionListData = [];
let currentFilter = 'all';
let wsRetryCount = 0;
const maxWsRetries = 3;
let listCountdownTimer = null;
let pollingInterval = null;

// Section: WebSocket Connection
function connectInteractionListWs() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = protocol + '://' + window.location.host + '/ws/interactions';
    debugLog('InteractionList', 'Connecting to WebSocket:', wsUrl);

    if (interactionListWs) {
        interactionListWs.close();
    }

    try {
        interactionListWs = new WebSocket(wsUrl);
    } catch (e) {
        console.error('[InteractionList] WebSocket creation error:', e);
        wsRetryCount++;
        if (wsRetryCount < maxWsRetries) {
            debugLog('InteractionList', 'Retrying in 3s, attempt:', wsRetryCount);
            setTimeout(connectInteractionListWs, 3000);
        }
        return;
    }

    interactionListWs.onopen = () => {
        debugLog('InteractionList', 'WebSocket connected successfully');
        wsRetryCount = 0;
    };

    interactionListWs.onerror = (e) => {
        console.error('[InteractionList] WebSocket error:', e);
        debugLog('InteractionList', 'WebSocket error event, target state:', interactionListWs?.readyState);
    };

    interactionListWs.onclose = (e) => {
        debugLog('InteractionList', 'WebSocket closed, code:', e.code, 'reason:', e.reason);
        wsRetryCount++;
        if (wsRetryCount < maxWsRetries) {
            debugLog('InteractionList', 'Retrying in 3s, attempt:', wsRetryCount);
            setTimeout(connectInteractionListWs, 3000);
        } else {
            debugLog('InteractionList', 'Max retries exceeded, falling back to polling');
            startPolling();
        }
    };

    interactionListWs.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            debugLog('InteractionList', 'Received message type:', data.type);
            if (data.type === 'list') {
                debugLog('InteractionList', 'Updating list with', data.interactions?.length || 0, 'items');
                interactionListData = data.interactions || [];
                renderInteractionList();
                startListCountdown();
            } else if (data.type === 'ping') {
                interactionListWs.send(JSON.stringify({ type: 'pong' }));
            }
        } catch (e) {
            console.error('[InteractionList] Parse error:', e);
        }
    };
}

// Section: Polling Fallback
function startPolling() {
    if (pollingInterval) return;
    pollingInterval = setInterval(fetchInteractionListFallback, 5000);
}

async function fetchInteractionListFallback() {
    debugLog('InteractionList', 'Fetching via REST API...');
    try {
        const response = await fetch('/api/interactions');
        if (response.ok) {
            const data = await response.json();
            debugLog('InteractionList', 'REST response:', data.interactions?.length || 0, 'items');
            if (data.interactions) {
                const currentId = window.mcpData.choiceId;
                const currentItem = data.interactions.find(i => i.session_id === currentId);
                if (currentItem) {
                    debugLog('InteractionList', 'Current session status:', currentItem.status);
                }
            }
            interactionListData = data.interactions || [];
            renderInteractionList();
            startListCountdown();
        } else {
            debugLog('InteractionList', 'REST fetch failed:', response.status);
        }
    } catch (e) {
        console.error('[InteractionList] Fallback fetch error:', e);
    }
}

// Section: Countdown
function startListCountdown() {
    if (listCountdownTimer) clearInterval(listCountdownTimer);
    listCountdownTimer = setInterval(() => {
        let updated = false;
        interactionListData = interactionListData.map(item => {
            if (item.status === 'pending' && typeof item.remaining_seconds === 'number') {
                const next = Math.max(0, item.remaining_seconds - 1);
                if (next !== item.remaining_seconds) {
                    updated = true;
                }
                return Object.assign({}, item, { remaining_seconds: next });
            }
            return item;
        });
        if (updated) {
            renderInteractionList();
        }
    }, 1000);
}

// Section: Toggle
function toggleInteractionList() {
    const toggle = document.getElementById('interactionToggle');
    const content = document.getElementById('interactionListContent');
    const card = toggle.closest('.card');
    const expanded = card.getAttribute('aria-expanded') === 'true';
    card.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    card.setAttribute('data-user-expanded', (!expanded).toString());
    toggle.classList.toggle('expanded', !expanded);
    content.classList.toggle('show', !expanded);
}

// Section: Filtering
function filterInteractions(filter) {
    currentFilter = filter;
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.filter === filter);
    });
    renderInteractionList();
}

// Section: Rendering
function renderInteractionList() {
    const container = document.getElementById('interactionListContent');
    if (!container) return;

    const choiceId = window.mcpData.choiceId;
    let filtered = interactionListData;

    if (currentFilter === 'active') {
        filtered = interactionListData.filter(i => i.status === 'pending');
    } else if (currentFilter === 'completed') {
        filtered = interactionListData.filter(i => i.status !== 'pending');
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div class="interaction-empty">No interactions</div>';
        return;
    }

    container.innerHTML = filtered.map(item => {
        const isCurrent = item.session_id === choiceId;
        const isTerminal = item.transport === 'terminal';
        const statusBadge = '<span class="interaction-badge badge-' + item.status + '">' + item.status.replace('_', ' ') + '</span>';
        const transportBadge = '<span class="interaction-badge badge-' + item.transport + '">' + item.transport + '</span>';
        // Terminal sessions are not clickable (no URL); only web sessions with URL are navigable
        const isClickable = !isTerminal && item.url;
        const clickAttr = isClickable ? 'data-session-id="' + item.session_id + '"' : '';
        const timeoutHint = item.status === 'pending' && typeof item.remaining_seconds === 'number'
            ? ' · timeout ~' + Math.ceil(item.remaining_seconds) + 's'
            : '';
        // Terminal-only label for pending terminal sessions
        const terminalOnlyLabel = isTerminal && item.status === 'pending'
            ? '<span class="interaction-badge badge-terminal-only">' + t('badge.terminal_only') + '</span>'
            : '';

        let progressBar = '';
        if (item.status === 'pending' && typeof item.remaining_seconds === 'number' && typeof item.timeout_seconds === 'number' && item.timeout_seconds > 0) {
            const pct = Math.max(0, Math.min(100, (item.remaining_seconds / item.timeout_seconds) * 100));
            const barClass = pct < 20 ? 'danger' : (pct < 50 ? 'warning' : '');
            progressBar = '<div class="interaction-progress"><div class="interaction-progress-bar ' + barClass + '" style="width:' + pct + '%"></div></div>';
        }

        // Add disabled class for terminal sessions to indicate non-interactive state
        const disabledClass = isTerminal ? ' disabled' : '';

        return '<div class="interaction-item' + (isCurrent ? ' current' : '') + disabledClass + '" ' + clickAttr + '>' +
            '<div class="interaction-item-header">' +
            '<span class="interaction-item-title">' + (item.title || 'Untitled') + '</span>' +
            statusBadge + transportBadge + terminalOnlyLabel +
            '</div>' +
            '<div class="interaction-item-meta">' + item.started_at + timeoutHint + '</div>' +
            progressBar +
            '</div>';
    }).join('');

    // Add click handlers for in-page navigation
    container.querySelectorAll('.interaction-item[data-session-id]').forEach(el => {
        el.addEventListener('click', () => {
            const sessionId = el.dataset.sessionId;
            if (sessionId && sessionId !== window.mcpData.choiceId) {
                navigateToInteraction(sessionId);
            }
        });
    });
}

// Section: In-Page Navigation
async function navigateToInteraction(sessionId) {
    debugLog('InteractionList', 'Navigating to interaction:', sessionId);

    // Start transition animation
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.classList.add('transitioning');
    }

    try {
        const response = await fetch('/api/interaction/' + sessionId);
        if (!response.ok) {
            console.error('[InteractionList] Failed to load interaction:', response.status);
            // Fallback to full page navigation
            window.location.href = '/choice/' + sessionId;
            return;
        }
        const data = await response.json();
        debugLog('InteractionList', 'Loaded interaction data:', data.choice_id);

        // Update window.mcpData with new interaction data
        updateMcpData(data);

        // Re-render the full UI
        if (typeof refreshFullUI === 'function') {
            refreshFullUI();
        } else if (typeof renderOptions === 'function') {
            renderOptions();
        }

        // Update URL without reload
        window.history.pushState({ sessionId: sessionId }, '', '/choice/' + sessionId);

        // Re-render interaction list to update current highlight
        renderInteractionList();

        // Re-establish WebSocket connection for the new session if it's active
        if (data.type === 'active' && typeof reconnectWebSocket === 'function') {
            reconnectWebSocket(sessionId);
        } else if (typeof disconnectWebSocket === 'function') {
            disconnectWebSocket();
        }

        debugLog('InteractionList', 'Navigation complete');
    } catch (e) {
        console.error('[InteractionList] Navigation error:', e);
        // Fallback to full page navigation
        window.location.href = '/choice/' + sessionId;
    } finally {
        // End transition animation
        if (mainContent) {
            // Small delay to allow the new content to be rendered before removing the class
            setTimeout(() => {
                mainContent.classList.remove('transitioning');
            }, 50);
        }
    }
}

function updateMcpData(data) {
    // Update core data
    window.mcpData.choiceId = data.choice_id;
    window.mcpData.promptTitle = data.title;
    window.mcpData.promptText = data.prompt;
    window.mcpData.selectionMode = data.selection_mode;
    window.mcpData.options = data.options;
    window.mcpData.allowTerminal = data.allow_terminal;
    window.mcpData.invocationTime = data.invocation_time;

    // Update session state
    window.mcpData.sessionState = data.session_state;

    // Update config
    if (data.config) {
        window.mcpData.defaults = window.mcpData.defaults || {};
        Object.assign(window.mcpData.defaults, data.config);
    }

    // Update timeout info
    if (typeof data.remaining_seconds === 'number') {
        window.mcpData.remainingSeconds = data.remaining_seconds;
    } else {
        window.mcpData.remainingSeconds = null;
    }

    // Update document title
    document.title = data.title + ' - Interactive Choice';
}

// Section: Initialize
function initializeInteractionList() {
    debugLog('InteractionList', 'Initializing...');
    connectInteractionListWs();
    fetchInteractionListFallback();

    // Handle browser back/forward navigation
    window.addEventListener('popstate', (event) => {
        if (event.state && event.state.sessionId) {
            navigateToInteraction(event.state.sessionId);
        }
    });
}
