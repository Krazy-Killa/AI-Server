// Settings -> Setup: upload and verify a signed release bundle. Verify-only:
// applying a staged release is a separate, not-yet-implemented step.

function describeSize(bytes) {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function initializeReleaseUpdates({ API_BASE, apiFetch }) {
    const fileInput = document.getElementById('setup-firmware-file');
    const verifyButton = document.getElementById('setup-firmware-verify');
    const status = document.getElementById('setup-firmware-status');
    const staged = document.getElementById('setup-firmware-staged');
    const setupTab = document.getElementById('settings-tab-setup');
    if (!fileInput || !verifyButton || !status || !staged || !setupTab) return;

    let enabled = false;
    let busy = false;

    function syncControls() {
        fileInput.disabled = !enabled || busy;
        verifyButton.disabled = !enabled || busy || fileInput.files.length === 0;
    }

    async function errorDetail(response) {
        try {
            const body = await response.json();
            if (typeof body.detail === 'string') return body.detail;
        } catch (_error) { /* fall through */ }
        return `The server returned status ${response.status}.`;
    }

    function renderStaged(records) {
        staged.replaceChildren();
        for (const record of records) {
            const row = document.createElement('div');
            row.className = 'settings-value settings-staged-release';
            const text = document.createElement('div');
            text.textContent = `Release ${record.release_id} (v${record.version}) verified. `
                + `Signer ${record.signer}. Payload sha256 ${record.payload_sha256}. `
                + `${record.file_count} files, ${describeSize(record.unpacked_bytes)} unpacked. `
                + `Expires ${new Date(record.expires_at * 1000).toLocaleString()}.`;
            const discard = document.createElement('button');
            discard.className = 'btn';
            discard.type = 'button';
            discard.textContent = 'Discard';
            discard.addEventListener('click', () => discardRelease(record.release_id));
            row.append(text, discard);
            staged.append(row);
        }
    }

    async function refresh() {
        try {
            const response = await apiFetch(`${API_BASE}/api/admin/updates`);
            if (!response.ok) throw new Error(await errorDetail(response));
            const body = await response.json();
            enabled = body.enabled === true;
            renderStaged(body.staged || []);
            if (!enabled) {
                status.textContent = 'Release verification is not configured on this server. '
                    + 'Set AI_SERVER_UPDATE_PUBLIC_KEYS, then redeploy.';
            } else if (!(body.staged || []).length) {
                status.textContent = 'Choose a signed release bundle (.aibundle) and select Verify. '
                    + 'Verification stages the bundle only; apply it at the server console with the operator runbook.';
            } else {
                status.textContent = 'Verified release staged. Applying is not available from the dashboard yet; '
                    + 'apply it at the server console with the operator runbook.';
            }
        } catch (error) {
            enabled = false;
            status.textContent = error instanceof Error ? error.message : 'Unable to load release status.';
        }
        syncControls();
    }

    async function discardRelease(releaseId) {
        busy = true;
        syncControls();
        try {
            const response = await apiFetch(
                `${API_BASE}/api/admin/updates/${encodeURIComponent(releaseId)}`,
                { method: 'DELETE' },
            );
            if (!response.ok) throw new Error(await errorDetail(response));
        } catch (error) {
            status.textContent = error instanceof Error ? error.message : 'Unable to discard the release.';
        } finally {
            busy = false;
        }
        await refresh();
    }

    verifyButton.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file || busy) return;
        busy = true;
        syncControls();
        status.textContent = `Uploading and verifying ${file.name} (${describeSize(file.size)})...`;
        try {
            const response = await apiFetch(`${API_BASE}/api/admin/updates`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/octet-stream' },
                body: file,
            });
            if (!response.ok) {
                status.textContent = `Rejected: ${await errorDetail(response)}`;
            } else {
                fileInput.value = '';
                busy = false;
                await refresh();
                return;
            }
        } catch (_error) {
            status.textContent = 'Upload failed. Check the connection and try again.';
        } finally {
            busy = false;
            syncControls();
        }
    });

    fileInput.addEventListener('change', syncControls);
    setupTab.addEventListener('click', refresh);
}
