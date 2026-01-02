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
let knownSessionIds = new Set(); // Track known sessions to detect new ones
let isInteractionSwitching = false;

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
        // Fetch fresh list after connection established to catch any updates
        // that occurred while the connection was being established
        fetchInteractionListFallback();
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

                // Check for new sessions and trigger notifications
                const newSessions = (data.interactions || []).filter(item =>
                    item.status === 'pending' && !knownSessionIds.has(item.session_id) && item.session_id !== window.mcpData.choiceId
                );

                if (newSessions.length > 0) {
                    const manager = getNotificationManager();
                    if (manager) {
                        newSessions.forEach(session => {
                            manager.notifyNewSession(session.session_id, session.title || session.prompt || '');
                        });
                    }
                    // Add new sessions to known set
                    newSessions.forEach(session => knownSessionIds.add(session.session_id));
                }

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

            // Check for new sessions and trigger notifications
            const newSessions = (data.interactions || []).filter(item =>
                item.status === 'pending' && !knownSessionIds.has(item.session_id) && item.session_id !== window.mcpData.choiceId
            );

            if (newSessions.length > 0) {
                const manager = getNotificationManager();
                if (manager) {
                    newSessions.forEach(session => {
                        manager.notifyNewSession(session.session_id, session.title || session.prompt || '');
                    });
                }
                // Add new sessions to known set
                newSessions.forEach(session => knownSessionIds.add(session.session_id));
            }

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

    // Clear loading state if present
    const loadingElement = container.querySelector('.interaction-empty');
    if (loadingElement) {
        loadingElement.remove();
    }

    // Get current session IDs in container for incremental updates
    const existingSessionIds = new Set();
    container.querySelectorAll('.interaction-item').forEach(el => {
        const sessionId = el.dataset.sessionId;
        if (sessionId) existingSessionIds.add(sessionId);
    });

    // Update or create items incrementally to preserve DOM for transitions
    filtered.forEach(item => {
        let element = container.querySelector(`.interaction-item[data-session-id="${item.session_id}"]`);

        const isCurrent = item.session_id === choiceId;
        const isTerminalOnly = item.interface === 'terminal';
        const isTerminalWeb = item.interface === 'terminal-web';
        const isClickable = item.url && (!isTerminalOnly || item.status !== 'pending');

        // Update progress bar and meta if exists
        if (element) {
            // Update current class to reflect the currently viewed interaction
            element.classList.toggle('current', isCurrent);

            const progressBar = element.querySelector('.interaction-progress-bar');
            const progressContainer = element.querySelector('.interaction-progress');
            const metaElement = element.querySelector('.interaction-item-meta');

            // For current session, use header timeout to ensure synchronization
            const displayRemaining = isCurrent ? window.mcpState.timeoutRemaining : item.remaining_seconds;
            const displayTimeout = isCurrent ? window.mcpState.timeoutTotal : item.timeout_seconds;

            // Update progress bar - remove if status is not pending, update width if pending
            if (item.status !== 'pending' && progressContainer) {
                progressContainer.remove();
            } else if (progressBar && item.status === 'pending' && typeof displayRemaining === 'number' && typeof displayTimeout === 'number' && displayTimeout > 0) {
                const pct = Math.max(0, Math.min(100, (displayRemaining / displayTimeout) * 100));
                const barClass = pct < 20 ? 'danger' : (pct < 50 ? 'warning' : '');
                progressBar.style.width = pct + '%';
                progressBar.className = 'interaction-progress-bar ' + barClass;
            }

            // Update timeout hint in meta
            if (metaElement) {
                const timeoutHint = item.status === 'pending' && typeof displayRemaining === 'number'
                    ? ' · Timeout: ' + Math.ceil(displayRemaining) + 's'
                    : '';
                metaElement.textContent = item.started_at + timeoutHint;
            }

            existingSessionIds.delete(item.session_id);
            return;
        }

        // Create new element if doesn't exist
        const statusBadge = '<span class="interaction-badge badge-' + item.status + '">' + item.status.replace('_', ' ') + '</span>';
        const transportBadge = '<span class="interaction-badge badge-' + item.interface + '">' + item.interface + '</span>';
        const clickAttr = isClickable ? 'data-session-id="' + item.session_id + '"' : '';

        // For current session, use header timeout to ensure synchronization
        const displayRemaining = isCurrent ? window.mcpState.timeoutRemaining : item.remaining_seconds;
        const displayTimeout = isCurrent ? window.mcpState.timeoutTotal : item.timeout_seconds;

        const timeoutHint = item.status === 'pending' && typeof displayRemaining === 'number'
            ? ' · Timeout: ' + Math.ceil(displayRemaining) + 's'
            : '';

        let progressBar = '';
        if (item.status === 'pending' && typeof displayRemaining === 'number' && typeof displayTimeout === 'number' && displayTimeout > 0) {
            const pct = Math.max(0, Math.min(100, (displayRemaining / displayTimeout) * 100));
            const barClass = pct < 20 ? 'danger' : (pct < 50 ? 'warning' : '');
            progressBar = '<div class="interaction-progress"><div class="interaction-progress-bar ' + barClass + '" style="width:' + pct + '%"></div></div>';
        }

        const disabledClass = !isClickable ? ' disabled' : '';

        // Add prompt preview if available
        let promptPreview = '';
        if (item.prompt) {
            // Simple markdown rendering for preview
            let previewText = item.prompt;
            if (previewText.length > 100) {
                previewText = previewText.substring(0, 100) + '...';
            }
            // Basic markdown formatting for preview
            previewText = previewText
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
            promptPreview = '<div class="interaction-item-preview">' + previewText + '</div>';
        }

        const newElement = document.createElement('div');
        newElement.className = 'interaction-item' + (isCurrent ? ' current' : '') + disabledClass;
        if (clickAttr) newElement.dataset.sessionId = item.session_id;
        newElement.innerHTML =
            '<div class="interaction-item-header">' +
            '<span class="interaction-item-title">' + (item.title || 'Untitled') + '</span>' +
            statusBadge + transportBadge +
            '</div>' +
            '<div class="interaction-item-meta">' + item.started_at + timeoutHint + '</div>' +
            promptPreview +
            progressBar;

        container.appendChild(newElement);
    });

    // Remove items that no longer exist
    existingSessionIds.forEach(sessionId => {
        const element = container.querySelector(`.interaction-item[data-session-id="${sessionId}"]`);
        if (element) element.remove();
    });

    // Add click handlers for in-page navigation (only for new elements without handler)
    container.querySelectorAll('.interaction-item[data-session-id]').forEach(el => {
        if (!el.dataset.clickBound) {
            el.addEventListener('click', handleInteractionClick);
            el.dataset.clickBound = 'true';
        }
    });
}

// Section: Click Handler
function handleInteractionClick(event) {
    const sessionId = event.currentTarget.dataset.sessionId;
    if (sessionId && sessionId !== window.mcpData.choiceId) {
        navigateToInteraction(sessionId);
    }
}

// Section: In-Page Navigation
async function navigateToInteraction(sessionId) {
    debugLog('InteractionList', 'Navigating to interaction:', sessionId);

    // Prevent overlapping navigation/animation
    if (isInteractionSwitching) return;
    isInteractionSwitching = true;

    // Start transition animation
    const mainColumn = document.querySelector('.main-column');
    if (mainColumn) {
        // Reset classes to allow animation replay and suppress base transitions during switch
        mainColumn.classList.add('interaction-animating');
        mainColumn.classList.remove('fade-in');
        mainColumn.classList.remove('transitioning');
        void mainColumn.offsetWidth;
        mainColumn.classList.add('transitioning');
    }

    // Ensure minimum transition time for visual continuity
    const minTransitionTime = new Promise(resolve => setTimeout(resolve, 220));

    try {
        const [response] = await Promise.all([
            fetch('/api/interaction/' + sessionId),
            minTransitionTime
        ]);

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
        // End transition animation - remove transitioning class to restore default state
        if (mainColumn) {
            void mainColumn.offsetWidth;
            mainColumn.classList.remove('transitioning');

            // Clean up guard class and reset state after animation completes
            setTimeout(() => {
                mainColumn.classList.remove('interaction-animating');
                isInteractionSwitching = false;
            }, 700);
        } else {
            isInteractionSwitching = false;
        }
    }
}

function updateMcpData(data) {
    console.log('DEBUG: updateMcpData called with:', data);

    // Update core data
    window.mcpData.choiceId = data.choice_id;
    window.mcpData.promptTitle = data.title;
    window.mcpData.promptText = data.prompt;
    window.mcpData.promptHtml = data.prompt_html;  // Add rendered HTML
    console.log('DEBUG: Set promptHtml to:', data.prompt_html);
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

    // Add current session to known set to avoid self-notification
    knownSessionIds.add(window.mcpData.choiceId);
}
