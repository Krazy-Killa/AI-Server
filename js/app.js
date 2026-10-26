import { initializeBackendLogs } from './backend-logs.js';
import { initializeOperations } from './operations.js';
import { initializeSystemMonitor } from './system-monitor.js';
import { initializeUiPreferences } from './ui-preferences.js';

// ===============================
// AI Dashboard — app.js (Expanded)
// ===============================

const isDashboardServer = window.location.port === '8001';
const API_BASE = window.AI_SERVER_API_BASE || (
    window.location.protocol === 'file:'
        ? 'http://127.0.0.1:8000'
        : isDashboardServer
            ? `${window.location.protocol}//${window.location.hostname}:8000`
            : window.location.origin
);
const authScreen = document.getElementById('auth-screen');
const authForm = document.getElementById('auth-form');
const authProvider = document.getElementById('auth-provider');
const authUsername = document.getElementById('auth-username');
const authPassword = document.getElementById('auth-password');
const authSubmit = document.getElementById('auth-submit');
const authNotice = document.getElementById('auth-notice');
const dashboardApp = document.getElementById('dashboard-app');
const authIdentity = document.getElementById('auth-identity');
const authLogout = document.getElementById('auth-logout');
const consoleNotice = document.getElementById('console-notice');
const consoleNoticeDismiss = document.getElementById('console-notice-dismiss');
let csrfToken = null;
let currentRole = null;
let refreshBackendLogs;
let refreshDiagnostics;
let refreshVmInventory;
let interfaceAuthor = '';
let releaseAuthGate;
let authGateReleased = false;
let authGate = new Promise(resolve => { releaseAuthGate = resolve; });

function holdAuthGate() {
    if (!authGateReleased) return;
    authGateReleased = false;
    authGate = new Promise(resolve => { releaseAuthGate = resolve; });
}

function releaseDashboardRequests() {
    if (authGateReleased) return;
    authGateReleased = true;
    releaseAuthGate();
}

function showLogin(message) {
    holdAuthGate();
    csrfToken = null;
    currentRole = null;
    interfaceAuthor = '';
    activeConversationId = null;
    chatHistoryLoaded = false;
    activeServerMode = null;
    currentPanelId = 'interface-panel';
    updateSidebarMode();
    sharedAdminMemory.hidden = true;
    sharedInsightList.replaceChildren();
    sharedInsightCount.textContent = '';
    sharedInsightStatus.textContent = '';
    sharedInsightContent.value = '';
    conversationSelect.replaceChildren(new Option('New conversation', ''));
    conversationDeleteButton.disabled = true;
    clearChatWindow();
    clearInterfaceWindow('Sign in to load the shared server console.');
    interfaceStatus.textContent = '';
    authNotice.textContent = message;
    authScreen.hidden = false;
    dashboardApp.hidden = true;
    authPassword.value = '';
    authUsername.focus();
}

consoleNoticeDismiss.addEventListener('click', () => {
    consoleNotice.hidden = true;
});

function applyAuthorizationUI(role, username, provider, csrf) {
    currentRole = role;
    csrfToken = csrf;
    interfaceAuthor = `${username} (${provider})`;
    authIdentity.textContent = `${username} · ${role} · ${provider}`;
    document.querySelector('[data-panel="interface-panel"]').hidden = role !== 'admin';
    document.querySelector('[data-panel="chat-panel"]').hidden = role === 'viewer';
    document.querySelector('[data-panel="backend-logs-panel"]').hidden = role !== 'admin';
    document.getElementById('diagnostics-run').hidden = role === 'viewer';
    document.getElementById('bot-restart').hidden = role !== 'admin';
    botApplyModelButton.disabled = role === 'viewer';
    const botLogs = document.getElementById('bot-log-window');
    if (botLogs) botLogs.hidden = role !== 'admin';
    if (role === 'viewer') {
        document.querySelector('[data-panel="system-panel"]').click();
    } else if (role === 'admin') {
        document.querySelector('[data-panel="interface-panel"]').click();
    } else {
        document.querySelector('[data-panel="chat-panel"]').click();
    }
    sharedAdminMemory.hidden = role !== 'admin';
    if (role === 'admin') loadSharedAdminInsights();
    authScreen.hidden = true;
    dashboardApp.hidden = false;
    releaseDashboardRequests();
}

async function apiFetch(url, options = {}) {
    await authGate;
    const headers = new Headers(options.headers || {});
    const method = (options.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
        headers.set('X-CSRF-Token', csrfToken);
    }
    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include',
    });
    if (response.status === 401 && !url.includes('/api/auth/')) {
        showLogin('Your session expired. Sign in again to continue.');
    }
    return response;
}

async function restoreSession() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/status`, {
            credentials: 'include',
        });
        const status = await response.json();
        if (!response.ok) throw new Error(status.detail || 'Could not check the dashboard session.');
        if (!status.authenticated) {
            showLogin('Sign in with a local dashboard account or Proxmox VE.');
            return;
        }
        applyAuthorizationUI(status.role, status.username, status.provider, status.csrf_token);
    } catch (error) {
        showLogin(error instanceof Error
            ? `Backend unavailable: ${error.message}`
            : 'Backend unavailable. Start the AI Server backend, then sign in.');
    }
}

authForm.addEventListener('submit', async event => {
    event.preventDefault();
    authSubmit.disabled = true;
    authNotice.textContent = 'Signing in…';
    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                provider: authProvider.value,
                username: authUsername.value,
                password: authPassword.value,
            }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `Sign-in failed (${response.status}).`);
        authPassword.value = '';
        applyAuthorizationUI(result.role, result.username, result.provider, result.csrf_token);
    } catch (error) {
        authNotice.textContent = error instanceof Error
            ? error.message
            : 'Sign-in failed. Check your credentials and try again.';
    } finally {
        authSubmit.disabled = false;
    }
});

authLogout.addEventListener('click', async () => {
    authLogout.disabled = true;
    try {
        const response = await apiFetch(`${API_BASE}/api/auth/logout`, { method: 'POST' });
        if (!response.ok) throw new Error('Sign out failed.');
        showLogin('You have been signed out.');
    } catch (error) {
        authNotice.textContent = error instanceof Error ? error.message : 'Sign out failed.';
    } finally {
        authLogout.disabled = false;
    }
});

// Cache DOM elements
const navItems = document.querySelectorAll('.nav-item');
const panels = document.querySelectorAll('.panel');

const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const interfaceWindow = document.getElementById('interface-window');
const interfaceInput = document.getElementById('interface-input');
const interfaceSendButton = document.getElementById('interface-send');
const interfaceStatus = document.getElementById('interface-status');
const interfacePanel = document.getElementById('interface-panel');
let interfaceRequestInProgress = false;
let interfaceLoadInProgress = false;
const researchMode = document.getElementById('research-mode');
const sidebarMode = document.getElementById('sidebar-mode');
let activeServerMode = null;
let currentPanelId = 'interface-panel';
const conversationSelect = document.getElementById('conversation-select');
const conversationNewButton = document.getElementById('conversation-new');
const conversationDeleteButton = document.getElementById('conversation-delete');
const conversationStatus = document.getElementById('conversation-status');
const sharedAdminMemory = document.getElementById('shared-admin-memory');
const sharedInsightList = document.getElementById('shared-insight-list');
const sharedInsightCount = document.getElementById('shared-insight-count');
const sharedInsightStatus = document.getElementById('shared-insight-status');
const sharedInsightForm = document.getElementById('shared-insight-form');
const sharedInsightContent = document.getElementById('shared-insight-content');

function updateSidebarMode() {
    const activityModes = {
        diagnostics: 'DIAG',
        maintenance: 'MAINT',
    };
    sidebarMode.textContent = activityModes[activeServerMode]
        || (currentPanelId === 'interface-panel'
            ? 'CONSOLE'
            : researchMode.checked ? 'RESEARCH' : 'LOCAL');
}

researchMode.addEventListener('change', updateSidebarMode);
updateSidebarMode();
const sharedInsightPublish = document.getElementById('shared-insight-publish');
let activeConversationId = null;
let chatRequestInProgress = false;
let chatHistoryLoaded = false;

// Bot panel elements
const botStatusEl = document.getElementById('bot-status');
const botLatencyEl = document.getElementById('bot-latency');
const botRestartTimeEl = document.getElementById('bot-restart-time');
const botLogWindow = document.getElementById('bot-log-window');
const botRestartButton = document.getElementById('bot-restart');
const botToggleCommandsButton = document.getElementById('bot-toggle-commands');
const botCommandsPanel = document.getElementById('bot-commands');
const botCommandList = document.getElementById('bot-command-list');
const botModelSelect = document.getElementById('bot-model-select');
const botApplyModelButton = document.getElementById('bot-apply-model');
const botFeedback = document.getElementById('bot-feedback');
let botCommands = [];
let botRestartPending = false;

// Model panel elements
const modelList = document.getElementById('model-list');
const modelRegistryStatus = document.getElementById('model-registry-status');
const activeModelLabel = document.getElementById('active-model-label');
const activeModelSelect = document.getElementById('active-model-select');
let modelSwitchInProgress = false;

// ===============================
// PANEL SWITCHING
// ===============================
navItems.forEach(item => {
    item.addEventListener('click', () => {
        currentPanelId = item.dataset.panel;
        updateSidebarMode();
        navItems.forEach(i => {
            i.classList.remove('active');
            i.removeAttribute('aria-current');
        });
        item.classList.add('active');
        item.setAttribute('aria-current', 'page');

        panels.forEach(panel => {
            const active = panel.id === item.dataset.panel;
            panel.style.display = active ? 'flex' : 'none';
            panel.classList.remove('panel-enter');
            if (active) {
                void panel.offsetWidth;
                panel.classList.add('panel-enter');
            }
        });
        if (item.dataset.panel === 'backend-logs-panel') refreshBackendLogs();
        if (item.dataset.panel === 'diagnostics-panel') refreshDiagnostics();
        if (item.dataset.panel === 'vms-panel') refreshVmInventory();
        if (item.dataset.panel === 'interface-panel') loadAdminInterface();
        if (item.dataset.panel === 'chat-panel' && currentRole !== 'viewer' && !chatHistoryLoaded) {
            chatHistoryLoaded = true;
            loadConversationList(null, true);
        }
    });
});

// Default: show chat panel only
panels.forEach(panel => {
    panel.style.display = panel.id === 'interface-panel' ? 'flex' : 'none';
});

// ===============================
// CHAT SYSTEM
// ===============================
function addMessage(
    text,
    sender = 'ai',
    latencyMs = null,
    sources = [],
    createdAt = null,
    targetWindow = chatWindow,
    author = null,
) {
    const emptyState = targetWindow.querySelector('.conversation-empty');
    if (emptyState) emptyState.remove();
    const msg = document.createElement('div');
    msg.classList.add('msg', sender === 'user' ? 'msg-user' : 'msg-ai');

    const label = document.createElement('div');
    label.classList.add('msg-label');
    label.textContent = sender === 'user' && author
        ? `ADMIN • ${author}`
        : sender === 'user' ? 'USER • CHAT' : 'AI • SYSTEM';

    const messageText = document.createElement('div');
    messageText.classList.add('msg-text');
    messageText.textContent = text;

    const timestamp = document.createElement('div');
    timestamp.classList.add('msg-timestamp');
    const timestampDate = typeof createdAt === 'number' ? new Date(createdAt * 1000) : new Date();
    const time = timestampDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    timestamp.textContent = typeof latencyMs === 'number'
        ? `${time} · ${(latencyMs / 1000).toFixed(2)}s`
        : time;

    msg.append(label, messageText);

    if (sender !== 'user' && Array.isArray(sources) && sources.length > 0) {
        const sourceList = document.createElement('div');
        sourceList.className = 'research-sources';
        const heading = document.createElement('div');
        heading.className = 'research-sources-title';
        heading.textContent = 'SOURCES';
        sourceList.appendChild(heading);

        sources.forEach((source, index) => {
            if (!source || typeof source.title !== 'string' || typeof source.url !== 'string') return;
            try {
                const url = new URL(source.url);
                if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
                const link = document.createElement('a');
                link.href = url.href;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.textContent = `[${index + 1}] ${source.title}`;
                if (source.page_status === 'fetched') {
                    link.title = 'Full page text retrieved for this answer';
                } else if (source.page_status === 'excerpt_only') {
                    link.title = 'Using the search-result excerpt only';
                }
                sourceList.appendChild(link);
            } catch {
                return;
            }
        });
        if (sourceList.childElementCount > 1) msg.appendChild(sourceList);
    }

    msg.appendChild(timestamp);

    targetWindow.appendChild(msg);
    targetWindow.scrollTop = targetWindow.scrollHeight;
    return msg;
}

function clearChatWindow() {
    chatWindow.replaceChildren();
    const emptyState = document.createElement('div');
    emptyState.className = 'conversation-empty';
    emptyState.textContent = 'Start a new chat or choose a saved conversation.';
    chatWindow.appendChild(emptyState);
}

function clearInterfaceWindow(message = 'No console activity yet. Send an operational request.') {
    interfaceWindow.replaceChildren();
    const emptyState = document.createElement('div');
    emptyState.className = 'conversation-empty';
    emptyState.textContent = message;
    interfaceWindow.appendChild(emptyState);
}

async function loadAdminInterface() {
    if (currentRole !== 'admin' || interfaceLoadInProgress || interfaceRequestInProgress) return;
    interfaceLoadInProgress = true;
    try {
        const response = await apiFetch(`${API_BASE}/api/interface/conversation`);
        const conversation = await response.json();
        if (!response.ok) throw new Error(conversation.detail || 'Could not load the shared console.');

        clearInterfaceWindow();
        const messages = Array.isArray(conversation.messages) ? conversation.messages : [];
        messages.forEach(message => {
            if (message.role !== 'user' && message.role !== 'assistant') return;
            addMessage(
                message.content,
                message.role,
                null,
                message.sources,
                message.created_at,
                interfaceWindow,
                message.author,
            );
        });
        if (!messages.length) clearInterfaceWindow();
        interfaceStatus.textContent = `Shared with admins · ${messages.length} messages`;
    } catch (error) {
        clearInterfaceWindow('The shared server console is unavailable.');
        interfaceStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not load the shared console.';
    } finally {
        interfaceLoadInProgress = false;
    }
}

async function sendInterfaceMessage() {
    if (currentRole !== 'admin' || interfaceRequestInProgress || modelSwitchInProgress) return;
    const text = interfaceInput.value.trim();
    if (!text) return;

    interfaceRequestInProgress = true;
    interfaceSendButton.disabled = true;
    interfaceInput.disabled = true;
    interfaceInput.value = '';
    addMessage(text, 'user', null, [], null, interfaceWindow, interfaceAuthor);
    const pendingReply = addMessage(
        'Processing server request…',
        'ai',
        null,
        [],
        null,
        interfaceWindow,
    );
    interfaceStatus.textContent = 'Sending request to the server interface…';
    try {
        const response = await apiFetch(`${API_BASE}/api/interface/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Server interface request failed.');
        if (typeof result.reply !== 'string') throw new Error('Server response did not contain a reply.');
        pendingReply.remove();
        interfaceRequestInProgress = false;
        await loadAdminInterface();
    } catch (error) {
        pendingReply.textContent = error instanceof Error
            ? `Error: ${error.message}`
            : 'Server interface request failed.';
        interfaceStatus.textContent = 'Request failed; refreshing the shared console.';
        interfaceRequestInProgress = false;
        await loadAdminInterface();
    } finally {
        interfaceRequestInProgress = false;
        interfaceSendButton.disabled = false;
        interfaceInput.disabled = false;
    }
}

async function loadConversationList(selectedId = activeConversationId, resumeLatest = false) {
    if (currentRole === 'viewer') return;
    try {
        const response = await apiFetch(`${API_BASE}/api/memory/conversations`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not load saved chats.');

        conversationSelect.replaceChildren(new Option('New conversation', ''));
        const conversations = Array.isArray(data.conversations) ? data.conversations : [];
        conversations.forEach(conversation => {
            if (typeof conversation.conversation_id !== 'string' || typeof conversation.title !== 'string') return;
            const option = new Option(`${conversation.title} (${conversation.message_count})`, conversation.conversation_id);
            conversationSelect.add(option);
        });
        const conversationToOpen = selectedId || (
            resumeLatest && conversations.length ? conversations[0].conversation_id : null
        );
        if (conversationToOpen && conversations.some(item => item.conversation_id === conversationToOpen)) {
            conversationSelect.value = conversationToOpen;
            activeConversationId = conversationToOpen;
            conversationDeleteButton.disabled = false;
            if (resumeLatest) await openConversation(conversationToOpen);
        } else {
            activeConversationId = null;
            conversationSelect.value = '';
            conversationDeleteButton.disabled = true;
            clearChatWindow();
        }
        conversationStatus.textContent = `${conversations.length} saved`;
    } catch (error) {
        conversationStatus.textContent = error instanceof Error ? error.message : 'Could not load saved chats.';
    }
}

async function openConversation(conversationId) {
    try {
        const response = await apiFetch(
            `${API_BASE}/api/memory/conversations/${encodeURIComponent(conversationId)}`
        );
        const conversation = await response.json();
        if (!response.ok) throw new Error(conversation.detail || 'Could not open this conversation.');
        clearChatWindow();
        for (const message of conversation.messages || []) {
            if (message.role !== 'user' && message.role !== 'assistant') continue;
            addMessage(
                message.content,
                message.role === 'user' ? 'user' : 'ai',
                null,
                message.sources,
                message.created_at,
            );
        }
        activeConversationId = conversationId;
        conversationSelect.value = conversationId;
        conversationDeleteButton.disabled = false;
        conversationStatus.textContent = conversation.title;
    } catch (error) {
        conversationSelect.value = activeConversationId || '';
        conversationStatus.textContent = error instanceof Error ? error.message : 'Could not open this conversation.';
    }
}

function startNewConversation() {
    activeConversationId = null;
    conversationSelect.value = '';
    conversationDeleteButton.disabled = true;
    conversationStatus.textContent = 'New chat';
    clearChatWindow();
}

async function ensureConversation() {
    if (activeConversationId) return activeConversationId;
    const response = await apiFetch(`${API_BASE}/api/memory/conversations`, {
        method: 'POST',
    });
    const conversation = await response.json();
    if (!response.ok) throw new Error(conversation.detail || 'Could not create a conversation.');
    activeConversationId = conversation.conversation_id;
    conversationSelect.add(
        new Option(`${conversation.title} (0)`, conversation.conversation_id),
        1,
    );
    conversationSelect.value = activeConversationId;
    conversationDeleteButton.disabled = false;
    conversationStatus.textContent = conversation.title;
    return activeConversationId;
}

async function deleteConversation() {
    if (!activeConversationId || !window.confirm('Delete this conversation and its saved messages?')) return;
    const conversationId = activeConversationId;
    conversationDeleteButton.disabled = true;
    try {
        const response = await apiFetch(
            `${API_BASE}/api/memory/conversations/${encodeURIComponent(conversationId)}`,
            { method: 'DELETE' },
        );
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Could not delete this conversation.');
        startNewConversation();
        await loadConversationList(null);
    } catch (error) {
        conversationStatus.textContent = error instanceof Error ? error.message : 'Could not delete this conversation.';
        conversationDeleteButton.disabled = false;
    }
}

conversationSelect.addEventListener('change', () => {
    if (conversationSelect.value) openConversation(conversationSelect.value);
    else startNewConversation();
});
conversationNewButton.addEventListener('click', startNewConversation);
conversationDeleteButton.addEventListener('click', deleteConversation);

async function loadSharedAdminInsights() {
    sharedInsightStatus.textContent = 'Loading shared notes…';
    sharedInsightList.replaceChildren();
    try {
        const response = await apiFetch(`${API_BASE}/api/memory/shared-insights`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Could not load shared admin notes.');

        const insights = Array.isArray(data.insights) ? data.insights : [];
        sharedInsightCount.textContent = `(${insights.length})`;
        if (!insights.length) {
            const empty = document.createElement('p');
            empty.className = 'shared-insight-empty';
            empty.textContent = 'No notes have been published.';
            sharedInsightList.appendChild(empty);
        }
        insights.forEach(insight => {
            if (!Number.isInteger(insight.insight_id) || typeof insight.content !== 'string') return;
            const item = document.createElement('article');
            item.className = 'shared-insight-item';
            const copy = document.createElement('div');
            copy.className = 'shared-insight-copy';
            copy.textContent = insight.content;
            const meta = document.createElement('div');
            meta.className = 'shared-insight-meta';
            const date = Number.isInteger(insight.created_at)
                ? new Date(insight.created_at * 1000).toLocaleString()
                : 'Date unavailable';
            meta.textContent = `Published by ${insight.created_by || 'admin'} · ${date}`;
            copy.appendChild(meta);

            const remove = document.createElement('button');
            remove.className = 'btn-secondary shared-insight-delete';
            remove.type = 'button';
            remove.textContent = 'Remove';
            remove.setAttribute('aria-label', 'Remove this shared insight');
            remove.addEventListener('click', () => deleteSharedInsight(insight.insight_id));
            item.append(copy, remove);
            sharedInsightList.appendChild(item);
        });
        sharedInsightStatus.textContent = '';
    } catch (error) {
        sharedInsightStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not load shared admin notes.';
    }
}

async function deleteSharedInsight(insightId) {
    if (!window.confirm('Remove this note from shared admin knowledge?')) return;
    sharedInsightStatus.textContent = 'Removing shared note…';
    try {
        const response = await apiFetch(
            `${API_BASE}/api/memory/shared-insights/${encodeURIComponent(insightId)}`,
            { method: 'DELETE' },
        );
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Could not remove the shared note.');
        await loadSharedAdminInsights();
        sharedInsightStatus.textContent = 'Shared note removed.';
    } catch (error) {
        sharedInsightStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not remove the shared note.';
    }
}

sharedInsightForm.addEventListener('submit', async event => {
    event.preventDefault();
    const content = sharedInsightContent.value.trim();
    if (!content) return;
    if (!window.confirm(
        'Publish this note to every admin? It will be available in admin chat context. ' +
        'Do not include private chat, credentials, or information that should not be shared.',
    )) return;

    sharedInsightPublish.disabled = true;
    sharedInsightStatus.textContent = 'Publishing shared note…';
    try {
        const response = await apiFetch(`${API_BASE}/api/memory/shared-insights`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Could not publish the shared note.');
        sharedInsightContent.value = '';
        await loadSharedAdminInsights();
        sharedInsightStatus.textContent = 'Note published to shared admin knowledge.';
    } catch (error) {
        sharedInsightStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not publish the shared note.';
    } finally {
        sharedInsightPublish.disabled = false;
    }
});

const backendStatusEl = document.getElementById('backend-status');

async function pollBackendStatus() {
    try {
        const response = await apiFetch(`${API_BASE}/api/system`, { method: "GET" });

        if (!response.ok) throw new Error("Backend offline");

        // If we reach here, backend is online
        backendStatusEl.textContent = "Online";
        backendStatusEl.classList.remove("backend-offline");
        backendStatusEl.classList.add("backend-online");

    } catch (err) {
        backendStatusEl.textContent = "Offline";
        backendStatusEl.classList.remove("backend-online");
        backendStatusEl.classList.add("backend-offline");
    }
}

// Poll every 3 seconds
setInterval(pollBackendStatus, 3000);
pollBackendStatus();

const WS_BASE = API_BASE.replace(/^http/, 'ws');

// Streams a reply over WebSocket. Rejects with { fallback: true } if the
// stream could not start, so the caller can use the REST endpoint instead.
function streamChat(text, thinkingMsg, conversationId) {
    return new Promise((resolve, reject) => {
        let socket;
        try {
            socket = new WebSocket(`${WS_BASE}/ws/chat`);
        } catch {
            reject({ fallback: true });
            return;
        }

        let replyEl = null;
        let textEl = null;
        let finished = false;

        const append = (content) => {
            if (!replyEl) {
                thinkingMsg.remove();
                replyEl = addMessage('', 'ai');
                textEl = replyEl.querySelector('.msg-text');
            }
            textEl.textContent += content;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        };

        socket.onopen = () => socket.send(JSON.stringify({
            message: text,
            conversation_id: conversationId,
        }));

        socket.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch {
                return;
            }
            if (data.type === 'token' && typeof data.content === 'string') {
                append(data.content);
            } else if (data.type === 'done') {
                finished = true;
                if (replyEl && typeof data.latency_ms === 'number') {
                    const stamp = replyEl.querySelector('.msg-timestamp');
                    stamp.textContent = `${stamp.textContent} · ${(data.latency_ms / 1000).toFixed(2)}s`;
                }
                socket.close();
                resolve();
            } else if (data.type === 'error') {
                finished = true;
                socket.close();
                if (replyEl) {
                    append(`\n[Error: ${data.detail || 'stream failed'}]`);
                    resolve();
                } else {
                    reject(new Error(data.detail || 'Chat stream failed.'));
                }
            }
        };

        socket.onclose = () => {
            if (finished) return;
            finished = true;
            if (replyEl) {
                append('\n[Connection lost before the reply finished.]');
                resolve();
            } else {
                reject({ fallback: true });
            }
        };
    });
}

async function requestReply(text, useResearch, conversationId) {
    const response = await apiFetch(`${API_BASE}${useResearch ? '/api/research' : '/api/chat'}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId })
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || `Chat request failed: ${response.status}`);
    }
    if (typeof data.reply !== 'string') throw new Error('Chat response did not contain a reply.');
    return data;
}

async function streamResearch(text, thinkingMsg, conversationId) {
    const response = await apiFetch(`${API_BASE}/api/research/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ message: text, conversation_id: conversationId }),
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Research request failed: ${response.status}`);
    }
    if (!response.body) throw new Error('Research stream is unavailable in this browser.');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const textEl = thinkingMsg.querySelector('.msg-text');
    let buffer = '';
    let reply = '';
    let sources = [];
    let completed = false;
    let latencyMs = null;

    function handleEvent(block) {
        let event = 'message';
        const dataLines = [];
        for (const line of block.split('\n')) {
            if (line.startsWith('event:')) event = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
        }
        if (dataLines.length === 0) return;
        const data = JSON.parse(dataLines.join('\n'));
        if (event === 'sources') {
            sources = Array.isArray(data.sources) ? data.sources : [];
        } else if (event === 'token' && typeof data.content === 'string') {
            reply += data.content;
            textEl.textContent = reply;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        } else if (event === 'done') {
            completed = true;
            latencyMs = Number.isFinite(data.latency_ms) ? data.latency_ms : null;
        } else if (event === 'error') {
            throw new Error(data.detail || 'Research stream failed.');
        }
    }

    try {
        while (!completed) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, '\n');
            let boundary;
            while ((boundary = buffer.indexOf('\n\n')) !== -1) {
                const block = buffer.slice(0, boundary);
                buffer = buffer.slice(boundary + 2);
                handleEvent(block);
            }
        }
        buffer = (buffer + decoder.decode()).replace(/\r\n/g, '\n');
        if (buffer.trim()) handleEvent(buffer);
    } finally {
        if (!completed) await reader.cancel().catch(() => {});
    }
    if (!completed) throw new Error('Research stream ended before the answer completed.');

    thinkingMsg.remove();
    addMessage(reply, 'ai', latencyMs, sources);
}

async function sendMessage() {
    if (modelSwitchInProgress || chatRequestInProgress) return;
    const text = chatInput.value.trim();
    if (!text) return;
    const useResearch = researchMode.checked;
    chatRequestInProgress = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;
    conversationSelect.disabled = true;
    conversationNewButton.disabled = true;
    conversationDeleteButton.disabled = true;

    addMessage(useResearch ? `WEB RESEARCH: ${text}` : text, 'user');
    chatInput.value = '';

    addMessage(useResearch ? 'Searching the web and preparing a cited answer…' : 'Processing request…', 'ai');
    const thinkingMsg = chatWindow.lastElementChild;
    let conversationId = null;

    try {
        conversationId = await ensureConversation();
        if (useResearch) {
            await streamResearch(text, thinkingMsg, conversationId);
        } else {
            try {
                await streamChat(text, thinkingMsg, conversationId);
            } catch (err) {
                if (!(err && err.fallback)) throw err;
                const data = await requestReply(text, false, conversationId);
                thinkingMsg.remove();
                addMessage(data.reply, 'ai', data.latency_ms, data.sources);
            }
        }
        await loadConversationList(conversationId);

    } catch (err) {
        thinkingMsg.remove();
        const message = err instanceof Error ? err.message : 'Unknown chat error.';
        addMessage(`Error: ${message}`, 'ai');
        if (conversationId) await loadConversationList(conversationId);
    } finally {
        chatRequestInProgress = false;
        sendBtn.disabled = modelSwitchInProgress;
        chatInput.disabled = modelSwitchInProgress;
        conversationSelect.disabled = false;
        conversationNewButton.disabled = false;
        conversationDeleteButton.disabled = !activeConversationId;
    }
}

sendBtn.addEventListener('click', sendMessage);
interfaceSendButton.addEventListener('click', sendInterfaceMessage);
interfaceInput.addEventListener('keypress', event => {
    if (event.key === 'Enter') sendInterfaceMessage();
});
chatInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') sendMessage();
});

// ===============================
// MODEL INVENTORY
// ===============================
function renderModelInventory(inventory) {
    const models = Array.isArray(inventory.models) ? inventory.models : [];
    const activeModel = models.find(model => model.id === inventory.active_model);

    activeModelLabel.textContent = activeModel
        ? `${modelSwitchInProgress ? 'Switching to' : 'Model:'} ${activeModel.name}`
        : 'Model: None loaded';
    modelRegistryStatus.textContent = modelSwitchInProgress
        ? 'Switching Model…'
        : `${models.length} ${models.length === 1 ? 'Model' : 'Models'} Installed`;

    activeModelSelect.replaceChildren();
    if (models.length === 0) {
        const option = document.createElement('option');
        option.textContent = 'No GGUF models installed';
        option.disabled = true;
        option.selected = true;
        activeModelSelect.appendChild(option);
    } else {
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.loaded
                ? `${model.name} — Loaded`
                : `${model.name} — Installed, not loaded`;
            option.selected = model.id === inventory.active_model;
            activeModelSelect.appendChild(option);
        });
    }

    activeModelSelect.disabled = currentRole === 'viewer' || modelSwitchInProgress || models.length === 0;

    modelList.replaceChildren();
    if (models.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'model-inventory-message';
        emptyMessage.textContent = 'No GGUF model files found in the configured model directory.';
        modelList.appendChild(emptyMessage);
    }

    models.forEach(model => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = `model-card${model.loaded ? ' model-card-loaded' : ''}`;
        card.dataset.modelId = model.id;
        card.setAttribute('aria-pressed', String(model.loaded));
        card.disabled = currentRole === 'viewer' || modelSwitchInProgress;

        const name = document.createElement('div');
        name.className = 'model-name';
        name.textContent = model.name;

        const status = document.createElement('div');
        status.className = 'model-status';
        status.textContent = modelSwitchInProgress && model.id === activeModelSelect.value
            ? 'SWITCHING MODEL…'
            : model.loaded ? 'LOADED IN LLAMA.CPP' : 'INSTALLED · CLICK TO LOAD';

        const metadata = document.createElement('div');
        metadata.className = 'model-meta';
        const format = document.createElement('span');
        format.textContent = model.format;
        const size = document.createElement('span');
        size.textContent = `${model.size_gib} GiB`;
        metadata.append(format, size);

        const filename = document.createElement('div');
        filename.className = 'model-filename';
        filename.textContent = model.filename;
        filename.title = model.filename;

        card.append(name, status, metadata, filename);
        modelList.appendChild(card);
    });

    if (inventory.runtime_error) {
        modelRegistryStatus.textContent = inventory.runtime_status === 'offline'
            ? 'llama.cpp Offline'
            : 'Runtime Model Unknown';
        modelRegistryStatus.title = inventory.runtime_error;
    } else {
        modelRegistryStatus.title = inventory.model_directory;
    }
}

async function loadModelInventory() {
    try {
        const response = await apiFetch(`${API_BASE}/api/models`);
        if (!response.ok) throw new Error(`Model inventory request failed: ${response.status}`);
        renderModelInventory(await response.json());
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown inventory error.';
        modelRegistryStatus.textContent = 'Inventory Unavailable';
        modelRegistryStatus.title = message;
        activeModelLabel.textContent = 'Model: Unavailable';
        activeModelSelect.replaceChildren();
        const option = document.createElement('option');
        option.textContent = 'Unable to load model inventory';
        option.disabled = true;
        option.selected = true;
        activeModelSelect.appendChild(option);
        modelList.replaceChildren();
        const errorMessage = document.createElement('div');
        errorMessage.className = 'model-inventory-message';
        errorMessage.textContent = message;
        modelList.appendChild(errorMessage);
    }
}

async function requestModelSwitch(modelId) {
    if (
        !modelId
        || currentRole === 'viewer'
        || modelSwitchInProgress
        || chatRequestInProgress
        || interfaceRequestInProgress
    ) return;

    modelSwitchInProgress = true;
    activeModelSelect.disabled = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;
    researchMode.disabled = true;
    interfaceSendButton.disabled = true;
    interfaceInput.disabled = true;
    modelRegistryStatus.textContent = 'Switching Model…';
    modelList.querySelectorAll('.model-card').forEach(card => {
        card.disabled = true;
    });

    let switchError = null;
    let activeModelId = null;
    try {
        const response = await apiFetch(`${API_BASE}/api/model/select`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.detail || `Model switch failed: ${response.status}`);
        }
        activeModelId = result.active_model;
    } catch (err) {
        switchError = err instanceof Error ? err.message : 'Unknown model switch error.';
    } finally {
        modelSwitchInProgress = false;
        sendBtn.disabled = false;
        chatInput.disabled = false;
        researchMode.disabled = false;
        interfaceSendButton.disabled = false;
        interfaceInput.disabled = false;
        await loadModelInventory();
    }

    if (switchError) {
        addMessage(`Model switch failed: ${switchError}`, 'ai');
    } else if (activeModelId) {
        modelRegistryStatus.textContent = `Active: ${activeModelId}`;
    }
}

activeModelSelect.addEventListener('change', () => {
    requestModelSwitch(activeModelSelect.value);
});

modelList.addEventListener('click', event => {
    const card = event.target.closest('.model-card');
    if (card instanceof HTMLButtonElement) {
        requestModelSwitch(card.dataset.modelId);
    }
});

loadModelInventory();

// ===============================
// BOT STATUS POLLING
// ===============================
async function pollBotStatus() {
    try {
        const response = await apiFetch(`${API_BASE}/api/bot/status`);
        if (!response.ok) throw new Error(`Bot status request failed: ${response.status}`);
        const data = await response.json();

        botStatusEl.textContent = data.online ? 'Status: Online' : 'Status: Offline';
        botStatusEl.classList.toggle('pill-success', data.online);
        botLatencyEl.textContent = Number.isFinite(data.latency_ms)
            ? `Latency: ${data.latency_ms}ms`
            : 'Latency: N/A';
        botRestartTimeEl.textContent = data.last_restart
            ? `Last restart: ${new Date(data.last_restart * 1000).toLocaleString()}`
            : 'Last restart: Unknown';
        botCommands = Array.isArray(data.commands) ? data.commands : [];
        if (botRestartPending && data.online && !data.restart_pending) {
            botRestartPending = false;
            botFeedback.textContent = 'Bot restarted and is back online.';
        }
        if (!botCommandsPanel.hidden) renderBotCommands();

    } catch (err) {
        botStatusEl.textContent = 'Status: Backend unavailable';
        botStatusEl.classList.remove('pill-success');
        botLatencyEl.textContent = 'Latency: N/A';
        botRestartTimeEl.textContent = 'Last restart: Unknown';
    }
}

setInterval(pollBotStatus, 3000);
pollBotStatus();

// ===============================
// BOT LOG STREAMING
// ===============================
async function pollBotLogs() {
    if (currentRole !== 'admin') return;
    try {
        const response = await apiFetch(`${API_BASE}/api/bot/logs`);
        if (!response.ok) throw new Error(`Bot logs request failed: ${response.status}`);
        const logs = await response.json();

        botLogWindow.replaceChildren();
        logs.forEach(line => {
            const logLine = document.createElement('div');
            logLine.classList.add('log-line');
            logLine.textContent = line;
            botLogWindow.appendChild(logLine);
        });
        botLogWindow.scrollTop = botLogWindow.scrollHeight;

    } catch (err) {
        const errorLine = document.createElement('div');
        errorLine.classList.add('log-line');
        errorLine.textContent = 'Unable to load logs.';
        botLogWindow.replaceChildren(errorLine);
    }
}

setInterval(pollBotLogs, 4000);
pollBotLogs();

// ===============================
function renderBotCommands() {
    botCommandList.replaceChildren();
    const commands = botCommands.length
        ? botCommands
        : ['No commands reported; confirm the bot is online.'];
    commands.forEach(command => {
        const item = document.createElement('li');
        item.textContent = `/${command}`;
        botCommandList.appendChild(item);
    });
}

botToggleCommandsButton.addEventListener('click', () => {
    const expanded = botToggleCommandsButton.getAttribute('aria-expanded') === 'true';
    botToggleCommandsButton.setAttribute('aria-expanded', String(!expanded));
    botToggleCommandsButton.textContent = expanded ? 'View Commands' : 'Hide Commands';
    botCommandsPanel.hidden = expanded;
    if (!expanded) renderBotCommands();
});

botRestartButton.addEventListener('click', async () => {
    botRestartButton.disabled = true;
    botFeedback.textContent = 'Sending restart request...';
    try {
        const response = await apiFetch(`${API_BASE}/api/bot/restart`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Restart failed (${response.status}).`);
        botRestartPending = true;
        botFeedback.textContent = 'Restart requested. Waiting for the bot to reconnect...';
        window.setTimeout(pollBotStatus, 1000);
    } catch (err) {
        botFeedback.textContent = err instanceof Error ? err.message : 'Unable to restart the bot.';
    } finally {
        botRestartButton.disabled = false;
    }
});

async function loadBotModels() {
    try {
        const response = await apiFetch(`${API_BASE}/api/models`);
        if (!response.ok) throw new Error(`Model inventory request failed: ${response.status}`);
        const inventory = await response.json();
        const models = Array.isArray(inventory.models) ? inventory.models : [];
        botModelSelect.replaceChildren();
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = `${model.name}${model.loaded ? ' (active)' : ''}`;
            option.selected = model.id === inventory.active_model;
            botModelSelect.appendChild(option);
        });
        if (!models.length) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No installed models';
            botModelSelect.appendChild(option);
        }
    } catch (err) {
        botModelSelect.replaceChildren(new Option('Models unavailable', ''));
        botFeedback.textContent = err instanceof Error ? err.message : 'Unable to load model inventory.';
    }
}

botApplyModelButton.addEventListener('click', async () => {
    const modelId = botModelSelect.value;
    if (!modelId) {
        botFeedback.textContent = 'Select an installed model first.';
        return;
    }

    botApplyModelButton.disabled = true;
    botFeedback.textContent = 'Switching the active server model...';
    try {
        const response = await apiFetch(`${API_BASE}/api/model/select`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId }),
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.detail || `Model switch failed (${response.status}).`);
        }
        botFeedback.textContent = `Active model changed to ${result.active_model}. This model is shared by dashboard and Discord chat.`;
        await Promise.all([loadBotModels(), loadModelInventory()]);
    } catch (err) {
        botFeedback.textContent = err instanceof Error ? err.message : 'Unable to switch the active model.';
        await loadBotModels();
    } finally {
        botApplyModelButton.disabled = false;
    }
});

loadBotModels();

refreshBackendLogs = initializeBackendLogs({ API_BASE, apiFetch });
({ refreshDiagnostics, refreshVmInventory } = initializeOperations({ API_BASE, apiFetch }));
initializeSystemMonitor({
    API_BASE,
    apiFetch,
    updateSidebarMode,
    setActiveServerMode: mode => { activeServerMode = mode; },
    shouldRefreshInterface: () => interfacePanel.style.display === 'flex' && currentRole === 'admin',
    loadAdminInterface,
});
initializeUiPreferences();
restoreSession();
