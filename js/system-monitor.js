import { setVisibleInterval } from './visibility.js';

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
    const cpuValue = document.getElementById('cpu-value');
    const gpuTelemetryStatus = document.getElementById('gpu-telemetry-status');
    const vramValue = document.getElementById('vram-value');
    const ramValue = document.getElementById('ram-value');
    const systemTrendsStatus = document.getElementById('system-trends-status');
    const systemTrendsDefaultStatus = systemTrendsStatus.textContent.trim();
    const trendSampleIntervalMs = 10_000;
    const trendWindowMs = 60 * 60 * 1000;
    let lastTrendSampleAt = 0;
    const trendSeries = [
        {
            key: 'gpu',
            read: data => data.gpu,
            scale: () => 100,
            format: value => `${value.toFixed(1)}%`,
            describe: value => `${value.toFixed(1)} percent`,
        },
        {
            key: 'vram',
            read: data => data.vram_used,
            scale: data => data.vram_total,
            format: (value, total) => `${value.toFixed(1)} / ${total.toFixed(1)} GB`,
            describe: (value, total) => `${value.toFixed(1)} GB of ${total.toFixed(1)} GB`,
        },
        {
            key: 'cpu',
            read: data => data.cpu,
            scale: () => 100,
            format: value => `${value.toFixed(1)}%`,
            describe: value => `${value.toFixed(1)} percent`,
        },
        {
            key: 'ram',
            read: data => data.ram,
            scale: () => 100,
            format: value => `${value.toFixed(1)}%`,
            describe: value => `${value.toFixed(1)} percent`,
        },
    ].map(series => ({
        ...series,
        samples: [],
        line: document.getElementById(`${series.key}-trend-line`),
        point: document.getElementById(`${series.key}-trend-point`),
        current: document.getElementById(`${series.key}-trend-current`),
        description: document.getElementById(`${series.key}-trend-description`),
    }));

    function renderTrendSeries(series, now) {
        const start = now - trendWindowMs;
        const validSamples = series.samples.filter(sample => sample.value !== null);
        const maximum = series.key === 'vram'
            ? Math.max(1, ...validSamples.map(sample => sample.scale))
            : 100;
        const left = 4;
        const right = 316;
        const top = 8;
        const bottom = 78;
        const width = right - left;
        const height = bottom - top;
        let path = '';
        let segmentOpen = false;
        let latest = null;
        let latestX = -10;
        let latestY = -10;

        for (const sample of series.samples) {
            if (sample.value === null) {
                segmentOpen = false;
                continue;
            }
            const x = left + ((sample.time - start) / trendWindowMs) * width;
            const value = Math.max(0, Math.min(maximum, sample.value));
            const y = bottom - (value / maximum) * height;
            path += `${segmentOpen ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)} `;
            segmentOpen = true;
            latest = sample;
            latestX = x;
            latestY = y;
        }

        series.line.setAttribute('d', path.trim());
        series.point.setAttribute('cx', latestX.toFixed(1));
        series.point.setAttribute('cy', latestY.toFixed(1));
        series.current.textContent = latest
            ? series.format(latest.value, latest.scale)
            : 'N/A';
        series.description.textContent = latest
            ? `Latest reading ${series.describe(latest.value, latest.scale)}. ${validSamples.length} samples in the current page session.`
            : 'No valid telemetry samples collected in the current page session.';
    }

    function recordTrendSample(data, now = Date.now()) {
        if (lastTrendSampleAt && now - lastTrendSampleAt < trendSampleIntervalMs) return;
        const hasGap = lastTrendSampleAt
            && now - lastTrendSampleAt > trendSampleIntervalMs * 1.5;
        const gapTime = hasGap ? lastTrendSampleAt + (now - lastTrendSampleAt) / 2 : null;

        for (const series of trendSeries) {
            if (gapTime !== null) {
                series.samples.push({ time: gapTime, value: null, scale: null });
            }
            const value = series.read(data);
            const scale = series.scale(data);
            const valid = typeof value === 'number'
                && Number.isFinite(value)
                && value >= 0
                && typeof scale === 'number'
                && Number.isFinite(scale)
                && scale > 0;
            series.samples.push({
                time: now,
                value: valid ? value : null,
                scale: valid ? scale : null,
            });
            series.samples = series.samples.filter(sample => sample.time >= now - trendWindowMs);
            renderTrendSeries(series, now);
        }
        lastTrendSampleAt = now;
    }

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
            systemTrendsStatus.textContent = systemTrendsDefaultStatus;
            recordTrendSample(data);

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
            const cpuText = typeof data.cpu === 'number' && Number.isFinite(data.cpu)
                ? `${data.cpu}%`
                : 'N/A';
            headerCpu.textContent = cpuText;
            cpuValue.textContent = cpuText;

        } catch (err) {
            console.error("System stats error:", err);
            systemTrendsStatus.textContent = 'Telemetry unavailable; charts retain prior samples from this session.';
            sidebarNodeName.textContent = 'UNAVAILABLE';
            sidebarGpuName.textContent = 'UNAVAILABLE';
            setActiveServerMode(null);
            updateSidebarMode();
            ramValue.textContent = 'N/A';
            setBarFill(ramBar, null);
            setBarFill(cpuBar, null);
            headerCpu.textContent = 'N/A';
            cpuValue.textContent = 'N/A';
        }
    }

    setVisibleInterval(pollSystemStats, 2000);
    pollSystemStats();
    setVisibleInterval(() => {
        if (shouldRefreshInterface()) loadAdminInterface();
    }, 5000);
}
