import { expect, test } from '@playwright/test';

async function installApiMocks(page, {
    loginRole = 'admin',
    rejectLogin = false,
    diagnosticsObservation = null,
    diagnosticsReportStatus = 200,
    modelInventory = {
        models: [],
        active_model: null,
        runtime_status: 'offline',
        runtime_error: 'llama.cpp is unavailable.',
        model_directory: 'test-models',
    },
} = {}) {
    let sessionRole = null;
    let requestedPaths = [];
    await page.route('**/api/**', async route => {
        const request = route.request();
        const url = new URL(request.url());
        requestedPaths.push(url.pathname);
        let body = {};
        let status = 200;

        if (url.pathname === '/api/auth/status') {
            body = {
                authenticated: Boolean(sessionRole),
                role: sessionRole,
                username: 'test-user',
                provider: 'local',
                csrf_token: 'test-csrf-token',
            };
        } else if (url.pathname === '/api/auth/login') {
            if (rejectLogin) {
                status = 401;
                body = { detail: 'Invalid credentials.' };
            } else {
                sessionRole = loginRole;
                body = {
                    role: sessionRole,
                    username: 'test-user',
                    provider: 'local',
                    csrf_token: 'test-csrf-token',
                };
            }
        } else if (url.pathname === '/api/auth/logout') {
            sessionRole = null;
            body = { success: true };
        } else if (url.pathname === '/api/system') {
            body = {
                node_name: 'test-node',
                gpu_adapter: 'test-gpu',
                gpu: 0,
                gpu_status: 'ok',
                gpu_engine: '3D',
                vram_used: 1,
                vram_total: 8,
                cpu: 5,
                ram: 25,
                activity_mode: null,
            };
        } else if (url.pathname === '/api/models') {
            body = modelInventory;
        } else if (url.pathname === '/api/bot/status') {
            body = {
                online: false,
                latency_ms: null,
                last_restart: null,
                commands: [],
                restart_pending: false,
            };
        } else if (url.pathname === '/api/bot/logs') {
            body = [];
        } else if (url.pathname === '/api/backend/logs') {
            body = { logs: [], count: 0 };
        } else if (url.pathname === '/api/diagnostics/status') {
            body = {
                status: diagnosticsObservation?.status || 'idle',
                latest_observation: diagnosticsObservation,
                open_incidents: 0,
            };
        } else if (url.pathname === '/api/diagnostics/incidents') {
            body = { incidents: [], open_incidents: 0 };
        } else if (url.pathname === '/api/diagnostics/report') {
            status = diagnosticsReportStatus;
            body = status === 200
                ? { report_version: 1, observation_id: diagnosticsObservation?.id }
                : { detail: 'Your session expired.' };
        } else if (url.pathname === '/api/proxmox/vms') {
            body = { configured: false };
        }

        await route.fulfill({
            status,
            contentType: 'application/json',
            body: JSON.stringify(body),
        });
    });

    return {
        requestedPaths: () => requestedPaths,
        resetRequestedPaths: () => { requestedPaths = []; },
    };
}

async function signIn(page, role) {
    await page.getByLabel('Username').fill('test-user');
    await page.getByLabel('Password').fill('test-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.locator('#dashboard-app')).toBeVisible();
    await expect(page.locator('#auth-identity')).toHaveText(`test-user · ${role} · local`);
}

test('loads every native module and keeps protected polling behind sign-in', async ({ page }) => {
    const api = await installApiMocks(page);
    const pageErrors = [];
    const policyViolations = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => {
        if (message.text().includes('Content Security Policy')) policyViolations.push(message.text());
    });

    await page.goto('/');
    await expect(page.locator('#auth-screen')).toBeVisible();
    await expect(page.locator('#dashboard-app')).toBeHidden();
    await expect(page.locator('#auth-notice')).toContainText('Sign in');

    await expect.poll(async () => page.evaluate(() => (
        performance.getEntriesByType('resource')
            .map(entry => new URL(entry.name).pathname)
            .filter(path => path.endsWith('.js'))
            .sort()
    ))).toEqual([
        '/js/app.js',
        '/js/backend-logs.js',
        '/js/operations.js',
        '/js/release-updates.js',
        '/js/system-monitor.js',
        '/js/theme-init.js',
        '/js/ui-preferences.js',
        '/js/visibility.js',
    ]);
    expect(api.requestedPaths()).toEqual(['/api/auth/status']);
    expect(pageErrors).toEqual([]);
    expect(policyViolations).toEqual([]);
});

test('shows rejected sign-in errors and keeps the dashboard locked', async ({ page }) => {
    await installApiMocks(page, { rejectLogin: true });
    await page.goto('/');
    await page.getByLabel('Username').fill('test-user');
    await page.getByLabel('Password').fill('wrong-password');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.locator('#auth-notice')).toHaveText('Invalid credentials.');
    await expect(page.locator('#auth-screen')).toBeVisible();
    await expect(page.locator('#dashboard-app')).toBeHidden();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeEnabled();
});

test('applies admin access and navigates between panels', async ({ page }) => {
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');

    await expect(page.locator('[data-panel="interface-panel"]')).toBeVisible();
    await expect(page.locator('[data-panel="backend-logs-panel"]')).toBeVisible();
    await page.locator('[data-panel="diagnostics-panel"]').click();
    await expect(page.locator('#diagnostics-panel')).toBeVisible();
    await expect(page.locator('#diagnostics-run')).toBeVisible();

    await page.locator('[data-panel="backend-logs-panel"]').click();
    await expect(page.locator('#backend-logs-panel')).toBeVisible();
    await expect(page.locator('[data-panel="backend-logs-panel"]')).toHaveAttribute('aria-current', 'page');

    await page.locator('[data-panel="settings-panel"]').click();
    await expect(page.locator('#settings-panel')).toBeVisible();
});

test('places shared admin knowledge in the AI Interface, not private AI Chat', async ({ page }) => {
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');

    const sharedKnowledge = page.locator('#shared-admin-memory');
    await expect(sharedKnowledge).toBeVisible();
    await expect(page.locator('#interface-panel #shared-admin-memory')).toHaveCount(1);
    await expect(page.locator('#chat-panel #shared-admin-memory')).toHaveCount(0);
    await sharedKnowledge.locator('summary').click();
    await expect(sharedKnowledge).toContainText('Notes published here are shared with all administrators');
    await expect(sharedKnowledge.locator('#shared-insight-list')).toContainText('No notes have been published.');

    await page.locator('[data-panel="chat-panel"]').click();
    await expect(page.locator('#chat-panel')).toBeVisible();
    await expect(page.locator('#shared-admin-memory')).toHaveCount(1);
    await expect(page.locator('#shared-admin-memory')).toBeHidden();
});

test('downloads a diagnostics report without navigating away from the panel', async ({ page }) => {
    await installApiMocks(page, {
        diagnosticsObservation: {
            id: 'obs-test',
            status: 'healthy',
            observed_at: '2026-11-05T12:00:00Z',
            resources: {},
            checks: [],
        },
    });
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="diagnostics-panel"]').click();
    await expect(page.locator('#diagnostics-report')).toBeEnabled();

    const navigations = [];
    page.on('framenavigated', frame => {
        if (frame === page.mainFrame()) navigations.push(frame.url());
    });
    const currentUrl = page.url();
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#diagnostics-report').click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toBe('diagnostics-obs-test.json');
    expect(page.url()).toBe(currentUrl);
    await expect(page.locator('#dashboard-app')).toBeVisible();
    expect(navigations).toEqual([]);
});

test('shares a prepared diagnostics file through the native share API when supported', async ({ page }) => {
    await page.addInitScript(() => {
        window.__sharedReport = null;
        Object.defineProperty(navigator, 'canShare', {
            configurable: true,
            value: data => Array.isArray(data.files) && data.files.length === 1,
        });
        Object.defineProperty(navigator, 'share', {
            configurable: true,
            value: async data => {
                const file = data.files[0];
                window.__sharedReport = {
                    name: file.name,
                    type: file.type,
                    userActivation: navigator.userActivation?.isActive,
                    content: await file.text(),
                };
            },
        });
    });
    await installApiMocks(page, {
        diagnosticsObservation: {
            id: 'obs-ios',
            status: 'healthy',
            observed_at: '2026-11-05T12:00:00Z',
            resources: {},
            checks: [],
        },
    });
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="diagnostics-panel"]').click();
    await expect(page.locator('#diagnostics-report')).toBeEnabled();

    const currentUrl = page.url();
    await page.locator('#diagnostics-report').click();
    await expect.poll(() => page.evaluate(() => window.__sharedReport?.name))
        .toBe('diagnostics-obs-ios.json');

    const sharedReport = await page.evaluate(() => window.__sharedReport);
    expect(sharedReport.type).toBe('application/json');
    expect(sharedReport.content).toContain('"observation_id": "obs-ios"');
    expect(sharedReport.userActivation).toBe(true);
    expect(page.url()).toBe(currentUrl);
    await expect(page.locator('#dashboard-app')).toBeVisible();
    await expect(page.locator('#diagnostics-notice')).toContainText('Save to Files');
});

test('shows the expired-session sign-in screen if report download returns 401', async ({ page }) => {
    await installApiMocks(page, {
        diagnosticsObservation: {
            id: 'obs-test',
            status: 'healthy',
            observed_at: '2026-11-05T12:00:00Z',
            resources: {},
            checks: [],
        },
        diagnosticsReportStatus: 401,
    });
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="diagnostics-panel"]').click();
    await page.locator('#diagnostics-report').click();

    await expect(page.locator('#auth-screen')).toBeVisible();
    await expect(page.locator('#auth-notice')).toHaveText('Your session expired. Sign in again to continue.');
    await expect(page.locator('#dashboard-app')).toBeHidden();
});

test('limits viewer navigation and controls to read-only access', async ({ page }) => {
    await installApiMocks(page, { loginRole: 'viewer' });
    await page.goto('/');
    await signIn(page, 'viewer');

    await expect(page.locator('#system-panel')).toBeVisible();
    await expect(page.locator('[data-panel="interface-panel"]')).toBeHidden();
    await expect(page.locator('[data-panel="chat-panel"]')).toBeHidden();
    await expect(page.locator('[data-panel="backend-logs-panel"]')).toBeHidden();
    await expect(page.locator('#diagnostics-run')).toBeHidden();
    await expect(page.locator('#bot-restart')).toBeHidden();
    await expect(page.locator('#bot-apply-model')).toBeDisabled();

    await page.reload();
    await expect(page.locator('#dashboard-app')).toBeVisible();
    await expect(page.locator('#system-panel')).toBeVisible();
});

test('allows operator chat while keeping administrator controls hidden', async ({ page }) => {
    await installApiMocks(page, { loginRole: 'operator' });
    await page.goto('/');
    await signIn(page, 'operator');

    await expect(page.locator('#chat-panel')).toBeVisible();
    await expect(page.locator('[data-panel="chat-panel"]')).toBeVisible();
    await expect(page.locator('[data-panel="interface-panel"]')).toBeHidden();
    await expect(page.locator('[data-panel="backend-logs-panel"]')).toBeHidden();
    await expect(page.locator('#shared-admin-memory')).toBeHidden();
    await page.locator('[data-panel="diagnostics-panel"]').click();
    await expect(page.locator('#diagnostics-panel')).toBeVisible();
    await expect(page.locator('#diagnostics-run')).toBeVisible();
    await expect(page.locator('#bot-restart')).toBeHidden();
});

test('settings sub-tabs switch views and gate the deployment tab to admins', async ({ page }) => {
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="settings-panel"]').click();

    await expect(page.locator('#settings-view-appearance')).toBeVisible();
    await page.locator('#settings-tab-network').click();
    await expect(page.locator('#settings-view-network')).toBeVisible();
    await expect(page.locator('#settings-view-appearance')).toBeHidden();
    await expect(page.locator('#settings-origin')).not.toHaveText('—');
    await page.locator('#settings-tab-network').press('ArrowRight');
    await expect(page.locator('#settings-tab-models')).toHaveAttribute('aria-selected', 'true');

    await page.locator('#settings-tab-setup').click();
    await expect(page.locator('#settings-view-setup')).toBeVisible();
    await expect(page.locator('#setup-firmware-file')).toBeDisabled();
    await expect(page.locator('#setup-firmware-apply')).toBeDisabled();

    await page.locator('#settings-tab-about').click();
    await expect(page.locator('#settings-view-about')).toBeVisible();
    await expect(page.locator('#about-version')).toHaveText('0.9.2');
    await expect(page.locator('#settings-view-about')).toContainText('read-only');
    await expect(page.locator('#settings-view-about a[href*="CHANGELOG.md"]')).toHaveAttribute('target', '_blank');

    await page.locator('#settings-tab-diagnostics').click();
    await page.locator('[data-settings-goto="diagnostics-panel"]').click();
    await expect(page.locator('#diagnostics-panel')).toBeVisible();
});

test('AI Chat header contains the model picker and reports Household AI readiness', async ({ page }) => {
    await installApiMocks(page, {
        modelInventory: {
            models: [{
                id: 'test-model.gguf',
                name: 'Test Model',
                filename: 'test-model.gguf',
                format: 'GGUF',
                size_gib: 1,
                loaded: true,
            }],
            active_model: 'test-model.gguf',
            runtime_status: 'online',
            runtime_error: null,
            model_directory: 'test-models',
        },
    });
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="chat-panel"]').click();

    await expect(page.locator('#chat-panel > .panel-header #active-model-select')).toHaveValue('test-model.gguf');
    await expect(page.locator('#household-ai-status-value')).toHaveText('Online');
    await expect(page.locator('#chat-panel [aria-label="Temperature"]')).toHaveCount(0);
});

test('AI Chat reports Household AI offline when no loaded model is available', async ({ page }) => {
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="chat-panel"]').click();

    await expect(page.locator('#household-ai-status-value')).toHaveText('Offline');
});

test('verifies and discards a signed release bundle without offering apply', async ({ page }) => {
    await installApiMocks(page);
    const staged = [];
    const seen = [];
    await page.route('**/api/admin/updates**', async route => {
        const request = route.request();
        const url = new URL(request.url());
        seen.push(`${request.method()} ${url.pathname} ${request.headers()['x-csrf-token'] || ''}`);
        if (request.method() === 'POST') {
            if (request.postDataBuffer()?.toString() === 'bad') {
                return route.fulfill({
                    status: 422, contentType: 'application/json',
                    body: JSON.stringify({ detail: 'Signature is not valid for any trusted signing key.' }),
                });
            }
            staged.push({
                release_id: '20261201-test', version: '9.9.9', signer: 'abcd1234abcd1234',
                payload_sha256: 'f'.repeat(64), file_count: 2, unpacked_bytes: 2048,
                expires_at: Date.now() / 1000 + 3600,
            });
            return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(staged[0]) });
        }
        if (request.method() === 'DELETE') {
            staged.length = 0;
            return route.fulfill({ status: 200, contentType: 'application/json', body: '{"discarded":"20261201-test"}' });
        }
        return route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ enabled: true, apply_supported: false, staged, limits: {} }),
        });
    });
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="settings-panel"]').click();
    await page.locator('#settings-tab-setup').click();

    await expect(page.locator('#setup-firmware-file')).toBeEnabled();
    await expect(page.locator('#setup-firmware-verify')).toBeDisabled();
    await page.locator('#setup-firmware-file').setInputFiles({
        name: 'bad.aibundle', mimeType: 'application/octet-stream', buffer: Buffer.from('bad'),
    });
    await page.locator('#setup-firmware-verify').click();
    await expect(page.locator('#setup-firmware-status')).toContainText('Rejected: Signature is not valid');

    await page.locator('#setup-firmware-file').setInputFiles({
        name: 'ok.aibundle', mimeType: 'application/octet-stream', buffer: Buffer.from('good'),
    });
    await page.locator('#setup-firmware-verify').click();
    await expect(page.locator('#setup-firmware-staged')).toContainText('20261201-test');
    await expect(page.locator('#setup-firmware-staged')).toContainText('abcd1234abcd1234');
    await expect(page.locator('#setup-firmware-apply')).toBeDisabled();
    expect(seen.some(entry => entry.startsWith('POST /api/admin/updates test-csrf-token'))).toBe(true);

    await page.locator('#setup-firmware-staged button').click();
    await expect(page.locator('#setup-firmware-staged')).toBeEmpty();
});

test('renders the VM inventory as a consistent table and as labelled rows on a phone', async ({ page }) => {
    await installApiMocks(page);
    await page.route('**/api/proxmox/vms', route => route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
            configured: true, count: 3, observed_at: '2026-11-05T12:00:00Z',
            guests: [
                { name: 'ai-host', vmid: 100, node: 'pve', type: 'QEMU VM', status: 'running' },
                { name: 'old-build', vmid: 101, node: 'pve', type: 'LXC container', status: 'stopped' },
                { name: '<img src=x onerror=alert(1)>', vmid: 102, node: 'pve', type: 'QEMU VM', status: 'paused' },
            ],
        }),
    }));
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="vms-panel"]').click();
    await page.locator('#vm-inventory-refresh').click();

    await expect(page.locator('#vm-connection-status')).toHaveClass(/pill-ok/);
    const rows = page.locator('#vm-inventory-rows tr');
    await expect(rows).toHaveCount(3);
    await expect(rows.nth(2).locator('.cell-name')).toHaveText('<img src=x onerror=alert(1)>');
    await expect(rows.nth(0).locator('.vm-state')).toHaveClass(/vm-state-running/);
    await expect(rows.nth(1).locator('.vm-state')).toHaveClass(/vm-state-stopped/);

    const sizes = await page.evaluate(() => [...document.querySelectorAll('#vm-inventory-rows td')]
        .map(cell => getComputedStyle(cell).fontSize));
    expect(new Set(sizes)).toEqual(new Set(['12px']));
    const headerSize = await page.locator('.infra-table th').first()
        .evaluate(cell => getComputedStyle(cell).fontSize);
    expect(headerSize).toBe('10px');

    await page.setViewportSize({ width: 390, height: 780 });
    await expect(page.locator('.infra-table thead')).toHaveCSS('position', 'absolute');
    await expect(rows.nth(0).locator('td').nth(1)).toHaveAttribute('data-label', 'VMID');
    const rowBox = await rows.nth(0).boundingBox();
    expect(rowBox.width).toBeLessThanOrEqual(390);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflow).toBe(false);
});

test('settings sign-out works from the Account tab on a phone viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 780 });
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');
    await expect(page.locator('#auth-logout')).toBeHidden();
    await page.locator('[data-panel="settings-panel"]').click();
    await page.locator('#settings-tab-account').click();
    await expect(page.locator('#settings-identity')).toContainText('admin');
    await page.locator('#settings-logout').click();
    await expect(page.locator('#auth-screen')).toBeVisible();
});

test('shows a readable message when sign-in gets a non-JSON throttle response', async ({ page }) => {
    await installApiMocks(page);
    await page.route('**/api/auth/login', route =>
        route.fulfill({ status: 429, contentType: 'text/html', body: '<html>429</html>' }));
    await page.goto('/');
    await page.getByLabel('Username').fill('test-user');
    await page.getByLabel('Password').fill('wrong-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.locator('#auth-notice')).toHaveText('Too many login attempts. Try again later.');
});

test('shows live CPU values instead of placeholders and a banner when the backend goes offline', async ({ page }) => {
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');
    await expect(page.locator('#cpu-header')).toHaveText('5%');
    await expect(page.locator('#cpu-value')).toHaveText('5%');
    await expect(page.locator('#connection-banner')).toBeHidden();

    await page.route('**/api/system', route => route.fulfill({ status: 503, body: '{}' }));
    await expect(page.locator('#connection-banner')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#connection-banner')).toContainText('backend is unreachable');
    await expect(page.locator('#cpu-header')).toHaveText('N/A');
});

test('serves self-hosted fonts and a web-app manifest without external requests', async ({ page }) => {
    const external = [];
    page.on('request', request => {
        if (!request.url().startsWith('http://127.0.0.1:4173')) external.push(request.url());
    });
    await installApiMocks(page);
    await page.goto('/');
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('link[rel="manifest"]')).toHaveAttribute('href', 'manifest.webmanifest');
    const manifest = await (await page.request.get('/manifest.webmanifest')).json();
    expect(manifest.display).toBe('standalone');
    for (const icon of manifest.icons) {
        expect((await page.request.get(icon.src)).ok()).toBe(true);
    }
    expect(external).toEqual([]);
});

test('hides the deployment settings tab from non-admin users', async ({ page }) => {
    await installApiMocks(page, { loginRole: 'operator' });
    await page.goto('/');
    await signIn(page, 'operator');
    await page.locator('[data-panel="settings-panel"]').click();

    await expect(page.locator('#settings-tab-setup')).toBeHidden();
    await expect(page.locator('#settings-tab-appearance')).toBeVisible();
});

test('persists theme, accent, and sidebar preferences across reloads', async ({ page }) => {
    await installApiMocks(page);
    await page.goto('/');
    await signIn(page, 'admin');
    await page.locator('[data-panel="settings-panel"]').click();

    await page.locator('#theme-toggle').click();
    await expect(page.locator('#theme-label')).toHaveText('Light / Daylight');
    await page.locator('.swatch.purple').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await page.locator('#sidebar-toggle').click();
    await expect(page.locator('#sidebar-toggle')).toHaveAttribute('aria-expanded', 'false');

    await page.reload();
    await expect(page.locator('#dashboard-app')).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await expect(page.locator('.swatch.purple')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('.app')).toHaveClass(/sidebar-collapsed/);
    await expect(page.locator('#sidebar-toggle')).toHaveAttribute('aria-expanded', 'false');
});
