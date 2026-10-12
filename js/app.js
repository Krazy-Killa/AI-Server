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

// Bot panel elements
const botStatusEl = document.querySelector('#bot-panel .pill-success');
const botLatencyEl = document.querySelector('#bot-panel .pill:nth-child(2)');
const botLogWindow = document.querySelector('#bot-panel .log-window');

// Model panel elements
const modelCards = document.querySelectorAll('.model-card');

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
function addMessage(text, sender = 'ai') {
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
    timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    msg.append(label, messageText, timestamp);

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
    const text = chatInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    chatInput.value = '';

    addMessage('Processing request…', 'ai');
    const thinkingMsg = chatWindow.lastElementChild;

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });

        if (!response.ok) throw new Error(`Chat request failed: ${response.status}`);
        const data = await response.json();
        if (typeof data.reply !== 'string') throw new Error('Chat response did not contain a reply.');
        thinkingMsg.remove();
        addMessage(data.reply, 'ai');

    } catch (err) {
        thinkingMsg.remove();
        addMessage("Error: Unable to reach AI backend.", 'ai');
    }
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') sendMessage();
});

// ===============================
// MODEL SWITCHING UI
// ===============================
modelCards.forEach(card => {
    card.addEventListener('click', async () => {
        const modelName = card.querySelector('.model-name').textContent;
        const modelId = card.dataset.modelId;

        try {
            const response = await fetch(`${API_BASE}/api/model/select`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model_id: modelId })
            });
            if (!response.ok) throw new Error(`Model selection failed: ${response.status}`);

            const result = await response.json();
            if (!result.success) throw new Error(`Backend rejected model: ${modelId}`);

            modelCards.forEach(c => c.style.borderColor = "var(--border-soft)");
            card.style.borderColor = "var(--accent)";
            addMessage(`Model switched to ${modelName}`, 'ai');
        } catch (err) {
            console.error("Model selection error:", err);
            addMessage(`Unable to switch to ${modelName}.`, 'ai');
        }
    });
});

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
    el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}

async function pollSystemStats() {
    try {
        const response = await fetch(`${API_BASE}/api/system`);
        const data = await response.json();

        setBarFill(gpuBar, data.gpu);
        setBarFill(cpuBar, data.cpu);
        setBarFill(ramBar, data.ram);

        const vramPercent = (data.vram_used / data.vram_total) * 100;
        setBarFill(vramBar, vramPercent);

        headerGpu.textContent = `${data.gpu}%`;
        headerCpu.textContent = `${data.cpu}%`;
        headerVram.textContent = `${data.vram_used} / ${data.vram_total}GB`;

    } catch (err) {
        console.error("System stats error:", err);
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
