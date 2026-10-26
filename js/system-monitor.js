export function initializeSystemMonitor({
    API_BASE,
    apiFetch,
    updateSidebarMode,
    setActiveServerMode,
    shouldRefreshInterface,
    loadAdminInterface,
}) {
    const sidebarNodeName = document.getElementById('sidebar-node-name');
    const sidebarGpuName = document.getElementById('sidebar-gpu-name');
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

    function setBarFill(el, percent) {
        if (typeof percent !== 'number' || !Number.isFinite(percent)) {
            el.style.width = '0%';
            return;
        }
        el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    }

    async function pollSystemStats() {
        try {
            const response = await apiFetch(`${API_BASE}/api/system`);
            if (!response.ok) throw new Error(`System stats request failed: ${response.status}`);
            const data = await response.json();

            sidebarNodeName.textContent = typeof data.node_name === 'string' && data.node_name.trim()
                ? data.node_name
                : 'UNAVAILABLE';
            sidebarGpuName.textContent = typeof data.gpu_adapter === 'string' && data.gpu_adapter.trim()
                ? data.gpu_adapter
                : data.gpu_status === 'checking' ? 'CHECKING' : 'UNAVAILABLE';
            setActiveServerMode(data.activity_mode === 'diagnostics'
                || data.activity_mode === 'maintenance'
                ? data.activity_mode
                : null);
            updateSidebarMode();

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
            sidebarNodeName.textContent = 'UNAVAILABLE';
            sidebarGpuName.textContent = 'UNAVAILABLE';
            setActiveServerMode(null);
            updateSidebarMode();
            ramValue.textContent = 'N/A';
            setBarFill(ramBar, null);
        }
    }

    setInterval(pollSystemStats, 2000);
    pollSystemStats();
    setInterval(() => {
        if (shouldRefreshInterface()) loadAdminInterface();
    }, 5000);
}
