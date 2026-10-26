export function initializeOperations({ API_BASE, apiFetch }) {
    const diagnosticsStatus = document.getElementById('diagnostics-status');
    const diagnosticsNotice = document.getElementById('diagnostics-notice');
    const diagnosticsRefreshButton = document.getElementById('diagnostics-refresh');
    const diagnosticsReportButton = document.getElementById('diagnostics-report');
    const diagnosticsRunButton = document.getElementById('diagnostics-run');
    const diagnosticsChecks = document.getElementById('diagnostics-checks');
    const diagnosticsIncidents = document.getElementById('diagnostics-incidents');
    const diagnosticsIncidentCount = document.getElementById('diagnostics-incident-count');
    const diagnosticsObservedAt = document.getElementById('diagnostics-observed-at');
    const vmConnectionStatus = document.getElementById('vm-connection-status');
    const vmInventoryStatus = document.getElementById('vm-inventory-status');
    const vmInventoryCount = document.getElementById('vm-inventory-count');
    const vmInventoryUpdated = document.getElementById('vm-inventory-updated');
    const vmInventoryRows = document.getElementById('vm-inventory-rows');
    const vmInventoryRefreshButton = document.getElementById('vm-inventory-refresh');
    let diagnosticsRequestInProgress = false;
    let diagnosticsLatestObservationId = null;
    let vmInventoryRequestInProgress = false;

    function formatBytes(bytes) {
        if (!Number.isFinite(bytes) || bytes < 0) return 'N/A';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let value = bytes;
        let unitIndex = 0;
        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024;
            unitIndex += 1;
        }
        return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    }

    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return Number.isNaN(date.getTime()) ? 'Unknown time' : date.toLocaleString();
    }

    function renderDiagnosticsObservation(observation) {
        if (!observation) {
            diagnosticsLatestObservationId = null;
            diagnosticsReportButton.disabled = true;
            diagnosticsChecks.replaceChildren();
            const empty = document.createElement('div');
            empty.className = 'diagnostics-empty';
            empty.textContent = 'Run an observation to check local services.';
            diagnosticsChecks.appendChild(empty);
            diagnosticsObservedAt.textContent = 'No observations';
            for (const id of ['diagnostics-cpu', 'diagnostics-ram', 'diagnostics-disk', 'diagnostics-rss']) {
                document.getElementById(id).textContent = 'N/A';
            }
            return;
        }

        diagnosticsLatestObservationId = observation.id;
        diagnosticsReportButton.disabled = !diagnosticsLatestObservationId;
        diagnosticsObservedAt.textContent = `Observed ${formatTimestamp(observation.observed_at)}`;
        const resources = observation.resources || {};
        document.getElementById('diagnostics-cpu').textContent =
            Number.isFinite(resources.cpu_percent) ? `${resources.cpu_percent.toFixed(1)}%` : 'N/A';
        document.getElementById('diagnostics-ram').textContent =
            Number.isFinite(resources.ram_percent) ? `${resources.ram_percent.toFixed(1)}%` : 'N/A';
        document.getElementById('diagnostics-disk').textContent =
            Number.isFinite(resources.log_disk_free_percent)
                ? `${resources.log_disk_free_percent.toFixed(1)}% (${formatBytes(resources.log_disk_free_bytes)})`
                : 'N/A';
        document.getElementById('diagnostics-rss').textContent = formatBytes(resources.backend_rss_bytes);

        diagnosticsChecks.replaceChildren();
        (Array.isArray(observation.checks) ? observation.checks : []).forEach(check => {
            const item = document.createElement('article');
            item.className = 'diagnostics-check';
            const heading = document.createElement('div');
            heading.className = 'diagnostics-check-heading';
            const name = document.createElement('strong');
            name.textContent = check.name;
            const state = document.createElement('span');
            state.className = `diagnostics-state diagnostics-state-${check.status}`;
            state.textContent = check.status;
            heading.append(name, state);
            const detail = document.createElement('p');
            detail.textContent = check.detail;
            const duration = document.createElement('small');
            duration.textContent = `${check.duration_ms} ms`;
            item.append(heading, detail, duration);
            diagnosticsChecks.appendChild(item);
        });
        if (!observation.checks?.length) {
            const empty = document.createElement('div');
            empty.className = 'diagnostics-empty';
            empty.textContent = 'No checks were configured.';
            diagnosticsChecks.appendChild(empty);
        }
        (Array.isArray(observation.thresholds) ? observation.thresholds : []).forEach(threshold => {
            const item = document.createElement('article');
            item.className = 'diagnostics-check';
            const heading = document.createElement('div');
            heading.className = 'diagnostics-check-heading';
            const name = document.createElement('strong');
            name.textContent = threshold.name;
            const state = document.createElement('span');
            state.className = `diagnostics-state diagnostics-state-${threshold.status}`;
            state.textContent = threshold.status;
            heading.append(name, state);
            const detail = document.createElement('p');
            detail.textContent = threshold.detail;
            item.append(heading, detail);
            diagnosticsChecks.appendChild(item);
        });
    }

    function renderDiagnosticsIncidents(incidents, openCount = null) {
        diagnosticsIncidents.replaceChildren();
        const actualOpenCount = Number.isFinite(openCount)
            ? openCount
            : incidents.filter(incident => incident.status === 'open').length;
        diagnosticsIncidentCount.textContent = `${actualOpenCount} open / ${incidents.length} shown`;
        if (!incidents.length) {
            const empty = document.createElement('div');
            empty.className = 'diagnostics-empty';
            empty.textContent = 'No incident history has been recorded.';
            diagnosticsIncidents.appendChild(empty);
            return;
        }

        incidents.slice().reverse().forEach(incident => {
            const item = document.createElement('article');
            item.className = 'diagnostics-incident';
            const heading = document.createElement('div');
            heading.className = 'diagnostics-check-heading';
            const name = document.createElement('strong');
            name.textContent = incident.check_name;
            const state = document.createElement('span');
            state.className = `diagnostics-state diagnostics-state-${incident.status}`;
            state.textContent = incident.status;
            heading.append(name, state);
            const detail = document.createElement('p');
            detail.textContent = incident.detail;
            const meta = document.createElement('small');
            meta.textContent = `First seen ${formatTimestamp(incident.first_seen)} · Last seen ${formatTimestamp(incident.last_seen)} · ${incident.occurrence_count} observation(s)`;
            item.append(heading, detail, meta);
            diagnosticsIncidents.appendChild(item);
        });
    }

    function renderVmInventory(guests) {
        vmInventoryRows.replaceChildren();
        if (!guests.length) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'infra-table-empty';
            cell.textContent = 'Connected, but no guests are visible to the configured inventory token.';
            row.appendChild(cell);
            vmInventoryRows.appendChild(row);
            return;
        }

        for (const guest of guests) {
            const row = document.createElement('tr');
            const values = [guest.name, guest.vmid, guest.type, guest.node, guest.status];
            for (const [index, value] of values.entries()) {
                const cell = document.createElement('td');
                const text = String(value);
                cell.textContent = index === 4
                    ? `${text.charAt(0).toUpperCase()}${text.slice(1)}`
                    : text;
                row.appendChild(cell);
            }
            vmInventoryRows.appendChild(row);
        }
    }

    async function refreshVmInventory() {
        if (vmInventoryRequestInProgress) return;
        vmInventoryRequestInProgress = true;
        vmInventoryRefreshButton.disabled = true;
        vmConnectionStatus.textContent = 'Loading inventory…';
        vmInventoryStatus.textContent = 'Loading';
        try {
            const response = await apiFetch(`${API_BASE}/api/proxmox/vms`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `Inventory request failed (${response.status}).`);
            }
            if (!data.configured) {
                vmConnectionStatus.textContent = 'Not configured';
                vmInventoryStatus.textContent = 'Not configured';
                vmInventoryCount.textContent = 'Not connected';
                vmInventoryUpdated.textContent = 'Not yet queried';
                vmInventoryRows.replaceChildren();
                const row = document.createElement('tr');
                const cell = document.createElement('td');
                cell.colSpan = 5;
                cell.className = 'infra-table-empty';
                cell.textContent = 'Configure a read-only Proxmox API token on the backend to enable inventory.';
                row.appendChild(cell);
                vmInventoryRows.appendChild(row);
                return;
            }
            if (!Array.isArray(data.guests) || !Number.isInteger(data.count)) {
                throw new Error('The backend returned an invalid inventory response.');
            }
            renderVmInventory(data.guests);
            vmConnectionStatus.textContent = 'Connected · read-only';
            vmInventoryStatus.textContent = 'Live inventory';
            vmInventoryCount.textContent = String(data.count);
            vmInventoryUpdated.textContent = data.observed_at
                ? new Date(data.observed_at).toLocaleString()
                : 'Unknown';
        } catch (error) {
            vmConnectionStatus.textContent = 'Unavailable';
            vmInventoryStatus.textContent = 'Request failed';
            vmInventoryCount.textContent = 'Unavailable';
            vmInventoryUpdated.textContent = 'Refresh to retry';
            vmInventoryRows.replaceChildren();
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'infra-table-empty';
            cell.textContent = error instanceof Error
                ? `Unable to load Proxmox inventory: ${error.message}`
                : 'Unable to load Proxmox inventory.';
            row.appendChild(cell);
            vmInventoryRows.appendChild(row);
        } finally {
            vmInventoryRequestInProgress = false;
            vmInventoryRefreshButton.disabled = false;
        }
    }

    vmInventoryRefreshButton.addEventListener('click', refreshVmInventory);

    async function refreshDiagnostics() {
        if (diagnosticsRequestInProgress) return;
        diagnosticsRequestInProgress = true;
        diagnosticsRefreshButton.disabled = true;
        diagnosticsRunButton.disabled = true;
        diagnosticsNotice.textContent = 'Loading observe-only diagnostics…';
        try {
            const [statusResponse, incidentsResponse] = await Promise.all([
                apiFetch(`${API_BASE}/api/diagnostics/status`),
                apiFetch(`${API_BASE}/api/diagnostics/incidents?status=all&limit=100`),
            ]);
            const [statusData, incidentsData] = await Promise.all([
                statusResponse.json(),
                incidentsResponse.json(),
            ]);
            if (!statusResponse.ok) {
                throw new Error(statusData.detail || `Diagnostics status failed (${statusResponse.status}).`);
            }
            if (!incidentsResponse.ok) {
                throw new Error(incidentsData.detail || `Diagnostics incidents failed (${incidentsResponse.status}).`);
            }
            if (!Array.isArray(incidentsData.incidents)) {
                throw new Error('Diagnostics incidents response was invalid.');
            }
            diagnosticsStatus.textContent = statusData.status.replaceAll('_', ' ');
            diagnosticsStatus.className = `pill diagnostics-pill-${statusData.status}`;
            diagnosticsNotice.textContent = 'Read-only checks only. No repairs or commands will be run. History is stored locally in the configured SQLite database.';
            renderDiagnosticsObservation(statusData.latest_observation);
            renderDiagnosticsIncidents(incidentsData.incidents, statusData.open_incidents);
        } catch (error) {
            diagnosticsStatus.textContent = 'Unavailable';
            diagnosticsStatus.className = 'pill';
            diagnosticsNotice.textContent = error instanceof Error
                ? `Unable to load diagnostics: ${error.message}`
                : 'Unable to load diagnostics.';
        } finally {
            diagnosticsRequestInProgress = false;
            diagnosticsRefreshButton.disabled = false;
            diagnosticsRunButton.disabled = false;
        }
    }

    async function runDiagnosticsObservation() {
        if (diagnosticsRequestInProgress) return;
        diagnosticsRequestInProgress = true;
        diagnosticsRefreshButton.disabled = true;
        diagnosticsRunButton.disabled = true;
        diagnosticsStatus.textContent = 'Running observe-only checks…';
        diagnosticsNotice.textContent = 'Collecting read-only health checks and resource evidence. No repairs or commands will be run.';
        try {
            const response = await apiFetch(`${API_BASE}/api/diagnostics/observe`, { method: 'POST' });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `Observation failed (${response.status}).`);
            }
            renderDiagnosticsObservation(data);
            try {
                await refreshDiagnosticsAfterObservation();
            } catch (refreshError) {
                diagnosticsStatus.textContent = data.status.replaceAll('_', ' ');
                diagnosticsNotice.textContent = refreshError instanceof Error
                    ? `Observation completed, but history could not be refreshed: ${refreshError.message}`
                    : 'Observation completed, but history could not be refreshed.';
            }
        } catch (error) {
            diagnosticsStatus.textContent = 'Observation failed';
            diagnosticsNotice.textContent = error instanceof Error
                ? `Unable to run observation: ${error.message}`
                : 'Unable to run observation.';
        } finally {
            diagnosticsRequestInProgress = false;
            diagnosticsRefreshButton.disabled = false;
            diagnosticsRunButton.disabled = false;
        }
    }

    async function downloadDiagnosticsReport() {
        if (!diagnosticsLatestObservationId || diagnosticsRequestInProgress) return;
        diagnosticsRequestInProgress = true;
        diagnosticsReportButton.disabled = true;
        diagnosticsNotice.textContent = 'Preparing the saved observe-only evidence report…';
        try {
            const response = await apiFetch(
                `${API_BASE}/api/diagnostics/report?observation_id=${encodeURIComponent(diagnosticsLatestObservationId)}`,
            );
            const report = await response.json();
            if (!response.ok) {
                throw new Error(report.detail || `Evidence report failed (${response.status}).`);
            }
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `diagnostics-${diagnosticsLatestObservationId}.json`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
            diagnosticsNotice.textContent = 'Evidence report downloaded. It contains recorded observations only; no diagnosis or actions were performed.';
        } catch (error) {
            diagnosticsNotice.textContent = error instanceof Error
                ? `Unable to download diagnostics report: ${error.message}`
                : 'Unable to download diagnostics report.';
        } finally {
            diagnosticsRequestInProgress = false;
            diagnosticsReportButton.disabled = !diagnosticsLatestObservationId;
        }
    }

    async function refreshDiagnosticsAfterObservation() {
        const [statusResponse, incidentsResponse] = await Promise.all([
            apiFetch(`${API_BASE}/api/diagnostics/status`),
            apiFetch(`${API_BASE}/api/diagnostics/incidents?status=all&limit=100`),
        ]);
        const [statusData, incidentsData] = await Promise.all([
            statusResponse.json(),
            incidentsResponse.json(),
        ]);
        if (!statusResponse.ok || !incidentsResponse.ok) {
            throw new Error('Observation completed, but diagnostics history could not be refreshed.');
        }
        diagnosticsStatus.textContent = statusData.status.replaceAll('_', ' ');
        diagnosticsStatus.className = `pill diagnostics-pill-${statusData.status}`;
        diagnosticsNotice.textContent = 'Read-only checks only. No repairs or commands will be run. History is stored locally in the configured SQLite database.';
        renderDiagnosticsObservation(statusData.latest_observation);
        renderDiagnosticsIncidents(incidentsData.incidents, statusData.open_incidents);
    }

    diagnosticsRefreshButton.addEventListener('click', refreshDiagnostics);
    diagnosticsReportButton.addEventListener('click', downloadDiagnosticsReport);
    diagnosticsRunButton.addEventListener('click', runDiagnosticsObservation);

    return { refreshDiagnostics, refreshVmInventory };
}
