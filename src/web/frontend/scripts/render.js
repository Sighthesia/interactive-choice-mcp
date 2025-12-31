/**
 * render.js - Option rendering and UI updates
 * Handles option display, selection, and annotations
 */

// Section: Markdown Helper
function renderMarkdown(text) {
    // Simple markdown rendering for session switching
    // For full markdown support, we rely on server-side rendering
    if (!text) return '';

    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');
}

// Section: Render Options
function getVisibleOptions() {
    return window.mcpData.options;
}

function renderOptions() {
    debugLog('Render', 'renderOptions called');
    const container = document.getElementById('options');
    if (!container) {
        console.error('[Render] Options container not found!');
        return;
    }

    container.innerHTML = '';
    const singleSubmit = isSingleSubmit();
    const useDefault = isUseDefaultOption();
    const visibleOpts = getVisibleOptions();
    const state = window.mcpState;

    debugLog('Render', 'Rendering', visibleOpts.length, 'options');

    if (state.focusedIndex >= visibleOpts.length) {
        state.focusedIndex = visibleOpts.length - 1;
    }
    if (state.focusedIndex < 0 && visibleOpts.length > 0) {
        state.focusedIndex = 0;
    }

    visibleOpts.forEach((opt, idx) => {
        const block = document.createElement('div');
        block.className = 'option' + (state.selectedIndices.has(opt.id) ? ' selected' : '');
        block.dataset.id = opt.id;
        block.tabIndex = 0;

        if (idx === state.focusedIndex) {
            block.classList.add('focused');
        }

        // Click handler for the whole option block
        block.onclick = (e) => {
            if (e.target.tagName === 'INPUT') return;
            state.focusedIndex = idx;
            updateFocusVisual();

            if (singleSubmit && window.mcpData.promptType !== 'multi') {
                submitPayload({
                    action_status: 'selected',
                    selected_indices: [opt.id],
                    option_annotations: state.optionAnnotations
                }, 'manual');
            } else {
                toggleOptionSelection(opt.id, block);
            }
        };

        if (window.mcpData.promptType === 'multi') {
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = opt.id;
            cb.checked = state.selectedIndices.has(opt.id);
            cb.onchange = (e) => {
                e.stopPropagation();
                if (cb.checked) state.selectedIndices.add(opt.id);
                else { state.selectedIndices.delete(opt.id); block.classList.remove('selected'); }
                block.classList.toggle('selected', cb.checked);
                updateSubmitBtn();
            };
            block.appendChild(cb);
        }

        const content = document.createElement('div');
        content.className = 'option-content';
        const recommendedLabel = t('label.recommended');
        const labelText = opt.recommended ? opt.id + ' (' + recommendedLabel + ')' : opt.id;
        content.innerHTML = '<div class="option-label">' + labelText + '</div><div class="option-desc">' + opt.description + '</div>';
        block.appendChild(content);

        const noteInput = document.createElement('input');
        noteInput.type = 'text';
        noteInput.placeholder = t('label.annotation');
        noteInput.className = 'option-note';
        noteInput.value = state.optionAnnotations[opt.id] || '';
        noteInput.addEventListener('input', () => {
            state.optionAnnotations[opt.id] = noteInput.value;
            updateCancelBtn();
        });
        noteInput.onclick = (e) => e.stopPropagation();
        block.appendChild(noteInput);

        container.appendChild(block);
    });

    updateSubmitBtn();
    updateCancelBtn();
}

// Section: Option Selection
function toggleOptionSelection(optionId, block) {
    const state = window.mcpState;
    if (state.selectedIndices.has(optionId)) {
        state.selectedIndices.delete(optionId);
        block.classList.remove('selected');
    } else {
        state.selectedIndices.add(optionId);
        block.classList.add('selected');
    }
    const cb = block.querySelector('input[type="checkbox"]');
    if (cb) cb.checked = state.selectedIndices.has(optionId);
    updateSubmitBtn();
}

function applyDefaultSelections() {
    const state = window.mcpState;
    state.selectedIndices.clear();
    if (isUseDefaultOption()) {
        getVisibleOptions().forEach(opt => {
            if (opt.recommended) {
                state.selectedIndices.add(opt.id);
            }
        });
    }
    renderOptions();
}

// Section: Focus Management
function updateFocusVisual() {
    const state = window.mcpState;
    document.querySelectorAll('.option').forEach((el, idx) => {
        el.classList.toggle('focused', idx === state.focusedIndex);
    });
}

function scrollOptionIntoView() {
    const focused = document.querySelector('.option.focused');
    if (focused) {
        focused.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
}

// Section: Button Updates
function updateSubmitBtn() {
    const singleSubmit = isSingleSubmit();
    const errorEl = document.getElementById('error');
    if (errorEl) errorEl.innerText = '';

    const btn = document.getElementById('submitBatchBtn');
    if (!btn) return;

    const isAutoSubmitActive = singleSubmit && window.mcpData.promptType !== 'multi';
    btn.disabled = isAutoSubmitActive;
    btn.innerText = isAutoSubmitActive ? t('action.submit_auto_single') : t('action.submit');
}

function hasAnnotations() {
    if (!isAnnotationEnabled()) return false;
    const g = document.getElementById('globalAnnotation')?.value || '';
    if (g && String(g).trim()) return true;
    return false;
}

function updateCancelBtn() {
    const btn = document.getElementById('cancelButton');
    if (!btn) return;
    if (hasAnnotations()) {
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-primary');
        btn.innerText = t('action.cancel_with_annotations');
    } else {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-danger');
        btn.innerText = t('action.cancel');
    }
}

function syncAnnotationVisibility() {
    renderOptions();
    updateCancelBtn();
}

// Section: Keyboard Navigation
function handleKeyNavigation(e) {
    const visible = getVisibleOptions();
    const optionCount = visible.length;
    if (optionCount === 0) return;

    const singleSubmit = isSingleSubmit();
    const state = window.mcpState;

    switch (e.key) {
        case 'ArrowDown':
        case 'j':
            e.preventDefault();
            state.focusedIndex = (state.focusedIndex + 1) % optionCount;
            updateFocusVisual();
            scrollOptionIntoView();
            break;

        case 'ArrowUp':
        case 'k':
            e.preventDefault();
            state.focusedIndex = state.focusedIndex <= 0 ? optionCount - 1 : state.focusedIndex - 1;
            updateFocusVisual();
            scrollOptionIntoView();
            break;

        case 'Enter':
            e.preventDefault();
            if (e.ctrlKey) {
                if (singleSubmit && window.mcpData.promptType !== 'multi' && state.focusedIndex >= 0) {
                    submitPayload({
                        action_status: 'selected',
                        selected_indices: [visible[state.focusedIndex].id],
                        option_annotations: state.optionAnnotations
                    }, 'manual');
                } else {
                    submitBatch('manual');
                }
            } else {
                if (state.focusedIndex >= 0 && state.focusedIndex < optionCount) {
                    const block = document.querySelector('.option[data-id="' + visible[state.focusedIndex].id + '"]');
                    if (singleSubmit && window.mcpData.promptType !== 'multi') {
                        submitPayload({
                            action_status: 'selected',
                            selected_indices: [visible[state.focusedIndex].id],
                            option_annotations: state.optionAnnotations
                        }, 'manual');
                    } else if (block) {
                        toggleOptionSelection(visible[state.focusedIndex].id, block);
                    }
                }
            }
            break;

        case 'Home':
            e.preventDefault();
            state.focusedIndex = 0;
            updateFocusVisual();
            scrollOptionIntoView();
            break;

        case 'End':
            e.preventDefault();
            state.focusedIndex = optionCount - 1;
            updateFocusVisual();
            scrollOptionIntoView();
            break;

        case 'A':
        case 'a':
            if (e.shiftKey) {
                e.preventDefault();
                if (state.focusedIndex >= 0 && state.focusedIndex < optionCount) {
                    const block = document.querySelector('.option[data-id="' + visible[state.focusedIndex].id + '"]');
                    if (block) {
                        const noteInput = block.querySelector('.option-note');
                        if (noteInput) noteInput.focus();
                    }
                }
            }
            break;
    }
}

// Section: Initialize Render
function initializeRender() {
    debugLog('Render', 'Initializing...');
    const defaults = window.mcpData.defaults;
    const state = window.mcpState;
    const options = window.mcpData.options;

    debugLog('Render', 'Options count:', options ? options.length : 0);
    debugLog('Render', 'hasFinalResult:', state.hasFinalResult);
    debugLog('Render', 'defaults.use_default_option:', defaults.use_default_option);

    // Set placeholder text
    const globalAnnotation = document.getElementById('globalAnnotation');
    if (globalAnnotation) {
        globalAnnotation.placeholder = t('hint.additional_annotation');
    }


    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            if (e.key === 'Escape') {
                e.target.blur();
                document.getElementById('options')?.focus();
            }
            return;
        }
        handleKeyNavigation(e);
    });

    // Focus options container on click
    const optionsContainer = document.getElementById('options');
    if (optionsContainer) {
        optionsContainer.addEventListener('click', () => optionsContainer.focus());
    }

    // Global annotation input handler
    if (globalAnnotation) {
        globalAnnotation.addEventListener('input', () => {
            updateCancelBtn();
            const section = globalAnnotation.closest('.annotation-section');
            if (section) {
                section.classList.toggle('has-content', globalAnnotation.value.trim());
            }
        });
    }

    // Single submit mode change handler
    const singleSubmitMode = document.getElementById('singleSubmitMode');
    if (singleSubmitMode) {
        singleSubmitMode.onchange = () => {
            renderOptions();
            updateConfigHighlights();
            updateSubmitBtn();
        };
    }

    // Use default option change handler
    const useDefaultToggle = document.getElementById('useDefaultOption');
    if (useDefaultToggle) {
        useDefaultToggle.checked = !!defaults.use_default_option;
        useDefaultToggle.onchange = () => {
            if (state.hasFinalResult) {
                updateConfigHighlights();
                return;
            }
            updateConfigHighlights();
            if (isUseDefaultOption()) {
                applyDefaultSelections();
            } else {
                renderOptions();
            }
        };
    }

    // Initial render
    if (state.hasFinalResult) {
        renderOptions();
        applyFinalizedState(state.sessionState);
    } else if (defaults.use_default_option) {
        applyDefaultSelections();
    } else {
        renderOptions();
    }

    syncAnnotationVisibility();

    // Auto-focus options for keyboard navigation
    setTimeout(() => {
        const opts = document.getElementById('options');
        if (opts) opts.focus();
        if (window.mcpData.options.length > 0) {
            state.focusedIndex = 0;
            updateFocusVisual();
        }
    }, 100);
}

// Section: Full UI Refresh (for in-page navigation)
function refreshFullUI() {
    debugLog('Render', 'refreshFullUI called');
    const state = window.mcpState;
    const data = window.mcpData;
    const sessionState = data.sessionState || {};

    console.log('DEBUG: refreshFullUI - data.promptTitle:', data.promptTitle);
    console.log('DEBUG: refreshFullUI - data.promptHtml:', data.promptHtml);
    console.log('DEBUG: refreshFullUI - data.promptText:', data.promptText);

    // Update page header
    const titleEl = document.querySelector('h1');
    if (titleEl) {
        console.log('DEBUG: Found title element, updating to:', data.promptTitle);
        titleEl.textContent = data.promptTitle || '';
    } else {
        console.log('DEBUG: Title element not found');
    }

    // Update prompt content - use server-rendered HTML if available, otherwise render client-side
    const promptEl = document.getElementById('prompt');
    if (promptEl) {
        console.log('DEBUG: Found prompt element');
        if (data.promptHtml) {
            console.log('DEBUG: Using server-rendered HTML');
            // Use server-rendered HTML if available
            promptEl.innerHTML = data.promptHtml;
        } else if (data.promptText) {
            console.log('DEBUG: Using client-side rendering');
            // Fallback to client-side rendering
            promptEl.innerHTML = renderMarkdown(data.promptText);
        } else {
            console.log('DEBUG: No prompt data available');
        }
    } else {
        console.log('DEBUG: Prompt element not found');
    }

    const timeEl = document.querySelector('.prompt-time');
    if (timeEl) timeEl.textContent = data.invocationTime || '';

    // Reset state
    state.selectedIndices = new Set(sessionState.selected_indices || []);
    state.optionAnnotations = sessionState.option_annotations || {};
    state.focusedIndex = 0;
    state.hasFinalResult = !!(sessionState.status && sessionState.status !== 'pending');
    state.sessionState = sessionState;
    state.submitting = false;

    // Update global annotation
    const globalAnnotation = document.getElementById('globalAnnotation');
    if (globalAnnotation) {
        globalAnnotation.value = sessionState.additional_annotation || '';
        globalAnnotation.disabled = state.hasFinalResult;

        // Update annotation section styling based on content
        const annotationSection = globalAnnotation.closest('.annotation-section');
        if (annotationSection) {
            const hasContent = !!(sessionState.additional_annotation && sessionState.additional_annotation.trim());
            annotationSection.classList.toggle('has-content', hasContent);
        }
    }

    // Clear any finalized state classes first
    document.body.classList.remove('submitted');
    document.querySelectorAll('.option').forEach(el => {
        el.classList.remove('finalized');
    });
    document.querySelectorAll('.card').forEach(card => {
        card.classList.remove('session-finalized');
    });

    // Hide status message
    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.style.display = 'none';
        statusEl.className = 'status';
        statusEl.innerText = '';
    }

    // Reset timeout display
    const timeoutContainer = document.getElementById('timeoutContainer');
    const timeoutBar = document.getElementById('timeoutProgressBar');
    const timeoutText = document.getElementById('timeoutText');
    if (timeoutContainer) {
        if (state.hasFinalResult) {
            timeoutContainer.style.display = 'none';
        } else {
            timeoutContainer.style.display = 'block';
        }
    }
    if (timeoutBar) {
        timeoutBar.classList.remove('success', 'warning', 'danger');
        timeoutBar.style.width = '100%';
    }
    if (timeoutText) {
        timeoutText.innerText = '';
    }

    // Reset notification flags only when session is finalized
    if (state.hasFinalResult) {
        state.notifiedThreshold = true;
        state.notifiedTimeout = true;
        state.timeoutExpired = true;
    }
    // Otherwise, preserve notification state across session switches

    // Stop any existing timeout timer
    if (typeof stopTimeout === 'function') {
        stopTimeout();
    }

    // Re-render options
    renderOptions();

    // Apply finalized state if needed
    if (state.hasFinalResult) {
        applyFinalizedState(sessionState);
    } else {
        // Re-enable form controls
        const submitBtn = document.getElementById('submitBatchBtn');
        const cancelBtn = document.getElementById('cancelButton');
        if (submitBtn) submitBtn.disabled = false;
        if (cancelBtn) cancelBtn.disabled = false;

        // Update submit button text based on mode
        updateSubmitBtn();
        updateCancelBtn();

        // Update connection status
        if (typeof updateConnectionStatus === 'function') {
            updateConnectionStatus(t('status.connected'), '');
        }

        // Restart timeout if there's remaining time
        if (typeof data.remainingSeconds === 'number' && data.remainingSeconds > 0) {
            if (typeof startTimeout === 'function') {
                startTimeout(data.remainingSeconds);
            }
        }
    }

    syncAnnotationVisibility();
    debugLog('Render', 'refreshFullUI complete');
}
