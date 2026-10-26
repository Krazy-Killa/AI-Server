export function initializeBackendLogs({ API_BASE, apiFetch }) {
    const backendLogsPanel = document.getElementById('backend-logs-panel');
    const backendLogsWindow = document.getElementById('backend-log-window');
    const backendLogsStatus = document.getElementById('backend-logs-status');
    const backendLogsRefreshButton = document.getElementById('backend-logs-refresh');
    let backendLogsRequestInProgress = false;

    async function refreshBackendLogs() {
        if (backendLogsRequestInProgress) return;
        backendLogsRequestInProgress = true;
        backendLogsRefreshButton.disabled = true;
        try {
            const response = await apiFetch(`${API_BASE}/api/backend/logs?limit=200`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `Backend logs request failed: ${response.status}`);
            }
            if (!Array.isArray(data.logs)) throw new Error('Backend logs response was invalid.');

            backendLogsWindow.replaceChildren();
            if (data.logs.length === 0) {
                const emptyLine = document.createElement('div');
                emptyLine.classList.add('log-line');
                emptyLine.textContent = 'No backend log entries yet.';
                backendLogsWindow.appendChild(emptyLine);
            } else {
                data.logs.forEach(line => {
                    const logLine = document.createElement('div');
                    logLine.classList.add('log-line');
                    logLine.textContent = line;
                    backendLogsWindow.appendChild(logLine);
                });
            }
            backendLogsStatus.textContent = `Showing ${data.count} entries`;
            backendLogsWindow.scrollTop = backendLogsWindow.scrollHeight;
        } catch (error) {
            const errorLine = document.createElement('div');
            errorLine.classList.add('log-line');
            errorLine.textContent = error instanceof Error
                ? `Unable to load backend logs: ${error.message}`
                : 'Unable to load backend logs.';
            backendLogsWindow.replaceChildren(errorLine);
            backendLogsStatus.textContent = 'Log viewer unavailable';
        } finally {
            backendLogsRequestInProgress = false;
            backendLogsRefreshButton.disabled = false;
        }
    }

    backendLogsRefreshButton.addEventListener('click', refreshBackendLogs);
    setInterval(() => {
        if (backendLogsPanel.style.display !== 'none') refreshBackendLogs();
    }, 5000);


    return refreshBackendLogs;
}
