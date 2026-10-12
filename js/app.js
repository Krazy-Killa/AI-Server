// ===============================
// AI Dashboard — app.js (Expanded)
// ===============================

const API_BASE = "http://127.0.0.1:8000";

// Cache DOM elements
const navItems = document.querySelectorAll('.nav-item');
const panels = document.querySelectorAll('.panel');

const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const researchMode = document.getElementById('research-mode');

// Bot panel elements
const botStatusEl = document.querySelector('#bot-panel .pill-success');
const botLatencyEl = document.querySelector('#bot-panel .pill:nth-child(2)');
const botLogWindow = document.querySelector('#bot-panel .log-window');

// Model panel elements
const modelList = document.getElementById('model-list');
const modelRegistryStatus = document.getElementById('model-registry-status');
const activeModelLabel = document.getElementById('active-model-label');
const activeModelSelect = document.getElementById('active-model-select');
let modelSwitchInProgress = false;

// Settings elements
const swatches = document.querySelectorAll('.swatch');
const root = document.documentElement;

// System monitor elements
const gpuBar = document.querySelector('.metric-bar-fill.gpu');
const vramBar = document.querySelector('.metric-bar-fill.vram');
const cpuBar = document.querySelector('.metric-bar-fill.cpu');
const ramBar = document.querySelector('.metric-bar-fill.ram');

const headerGpu = document.querySelector('.header-metrics div:nth-child(1) .metric-value');
const headerVram = document.querySelector('.header-metrics div:nth-child(2) .metric-value');
const headerCpu = document.querySelector('.header-metrics div:nth-child(3) .metric-value');
const gpuLoadValue = document.getElementById('gpu-load-value');
const gpuTelemetryStatus = document.getElementById('gpu-telemetry-status');
const vramValue = document.getElementById('vram-value');
const ramValue = document.getElementById('ram-value');

// ===============================
// PANEL SWITCHING
// ===============================
navItems.forEach(item => {
    item.addEventListener('click', () => {
        navItems.forEach(i => {
            i.classList.remove('active');
            i.removeAttribute('aria-current');
        });
        item.classList.add('active');
        item.setAttribute('aria-current', 'page');

        panels.forEach(panel => {
            panel.style.display = panel.id === item.dataset.panel ? 'flex' : 'none';
        });
    });
});

// Default: show chat panel only
panels.forEach(panel => {
    panel.style.display = panel.id === 'chat-panel' ? 'flex' : 'none';
});

// ===============================
// CHAT SYSTEM
// ===============================
function addMessage(text, sender = 'ai', latencyMs = null, sources = []) {
    const msg = document.createElement('div');
    msg.classList.add('msg', sender === 'user' ? 'msg-user' : 'msg-ai');

    const label = document.createElement('div');
    label.classList.add('msg-label');
    label.textContent = sender === 'user' ? 'USER • COMMAND' : 'AI • SYSTEM';

    const messageText = document.createElement('div');
    messageText.classList.add('msg-text');
    messageText.textContent = text;

    const timestamp = document.createElement('div');
    timestamp.classList.add('msg-timestamp');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
                sourceList.appendChild(link);
            } catch {
                return;
            }
        });
        if (sourceList.childElementCount > 1) msg.appendChild(sourceList);
    }

    msg.appendChild(timestamp);

    chatWindow.appendChild(msg);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

const backendStatusEl = document.getElementById('backend-status');

async function pollBackendStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/system`, { method: "GET" });

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

async function sendMessage() {
    if (modelSwitchInProgress) return;
    const text = chatInput.value.trim();
    if (!text) return;
    const useResearch = researchMode.checked;

    addMessage(useResearch ? `WEB RESEARCH: ${text}` : text, 'user');
    chatInput.value = '';

    addMessage(useResearch ? 'Searching the web and preparing a cited answer…' : 'Processing request…', 'ai');
    const thinkingMsg = chatWindow.lastElementChild;

    try {
        const response = await fetch(`${API_BASE}${useResearch ? '/api/research' : '/api/chat'}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || `Chat request failed: ${response.status}`);
        }
        if (typeof data.reply !== 'string') throw new Error('Chat response did not contain a reply.');
        thinkingMsg.remove();
        addMessage(data.reply, 'ai', data.latency_ms, data.sources);

    } catch (err) {
        thinkingMsg.remove();
        const message = err instanceof Error ? err.message : 'Unknown chat error.';
        addMessage(`Error: ${message}`, 'ai');
    }
}

sendBtn.addEventListener('click', sendMessage);
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
    activeModelSelect.disabled = modelSwitchInProgress || models.length === 0;

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
        card.disabled = modelSwitchInProgress;

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
        const response = await fetch(`${API_BASE}/api/models`);
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
    if (!modelId || modelSwitchInProgress) return;

    modelSwitchInProgress = true;
    activeModelSelect.disabled = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;
    researchMode.disabled = true;
    modelRegistryStatus.textContent = 'Switching Model…';
    modelList.querySelectorAll('.model-card').forEach(card => {
        card.disabled = true;
    });

    let switchError = null;
    let activeModelId = null;
    try {
        const response = await fetch(`${API_BASE}/api/model/select`, {
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
        const response = await fetch(`${API_BASE}/api/bot/status`);
        const data = await response.json();

        botStatusEl.textContent = data.online ? "Status: Online" : "Status: Offline";
        botLatencyEl.textContent = `Latency: ${data.latency_ms}ms`;

    } catch (err) {
        botStatusEl.textContent = "Status: Offline";
        botLatencyEl.textContent = "Latency: N/A";
    }
}

setInterval(pollBotStatus, 3000);
pollBotStatus();

// ===============================
// BOT LOG STREAMING
// ===============================
async function pollBotLogs() {
    try {
        const response = await fetch(`${API_BASE}/api/bot/logs`);
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
// SYSTEM STATS POLLING
// ===============================
function setBarFill(el, percent) {
    if (typeof percent !== 'number' || !Number.isFinite(percent)) {
        el.style.width = '0%';
        return;
    }
    el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}

async function pollSystemStats() {
    try {
        const response = await fetch(`${API_BASE}/api/system`);
        if (!response.ok) throw new Error(`System stats request failed: ${response.status}`);
        const data = await response.json();

        setBarFill(gpuBar, data.gpu);
        setBarFill(cpuBar, data.cpu);
        setBarFill(ramBar, data.ram);
        ramValue.textContent = typeof data.ram === 'number' && Number.isFinite(data.ram)
            ? `${data.ram.toFixed(1)}%`
            : 'N/A';

        const hasVramStats = typeof data.vram_used === 'number'
            && Number.isFinite(data.vram_used)
            && typeof data.vram_total === 'number'
            && Number.isFinite(data.vram_total)
            && data.vram_total > 0;
        const vramPercent = hasVramStats ? (data.vram_used / data.vram_total) * 100 : null;
        setBarFill(vramBar, vramPercent);
        const vramText = hasVramStats
            ? `${data.vram_used.toFixed(1)} / ${data.vram_total.toFixed(1)} GB`
            : 'N/A';
        headerVram.textContent = vramText;
        vramValue.textContent = vramText;

        const gpuLoadText = typeof data.gpu === 'number' && Number.isFinite(data.gpu)
            ? `${data.gpu}%`
            : 'N/A';
        headerGpu.textContent = gpuLoadText;
        gpuLoadValue.textContent = gpuLoadText;
        gpuTelemetryStatus.textContent = data.gpu_status === 'ok'
            ? 'GPU / LIVE'
            : data.gpu_status === 'checking'
                ? 'GPU / CHECKING'
                : 'GPU / UNAVAILABLE';
        gpuTelemetryStatus.title = data.gpu_status === 'ok'
            ? `${data.gpu_adapter} · Peak engine: ${data.gpu_engine}`
            : data.gpu_error || 'GPU utilization is unavailable.';
        headerCpu.textContent = `${data.cpu}%`;
        headerVram.textContent = `${data.vram_used} / ${data.vram_total}GB`;

    } catch (err) {
        console.error("System stats error:", err);
        ramValue.textContent = 'N/A';
        setBarFill(ramBar, null);
    }
}

setInterval(pollSystemStats, 2000);
pollSystemStats();

// ===============================
// SETTINGS — ACCENT COLOR SWITCHING
// ===============================
swatches.forEach(swatch => {
    swatch.addEventListener('click', () => {
        const color = getComputedStyle(swatch).backgroundColor;
        root.style.setProperty('--accent', color);
    });
});

// ===============================
// SETTINGS — THEME SWITCHING (Dark/Light)
// ===============================
function applyTheme(theme) {
    if (theme === "light") {
        root.style.setProperty('--bg-main', '#f0f0f0');
        root.style.setProperty('--bg-panel', '#ffffff');
        root.style.setProperty('--text-main', '#000000');
        root.style.setProperty('--text-muted', '#555555');
    } else {
        root.style.setProperty('--bg-main', '#0b0f16');
        root.style.setProperty('--bg-panel', '#141922');
        root.style.setProperty('--text-main', '#e0e0e0');
        root.style.setProperty('--text-muted', '#9aa0b5');
    }
}

// Example theme toggle (you can wire this to a button later)
applyTheme("dark");
