import { expect, test } from '@playwright/test';

async function installApiMocks(page, { loginRole = 'admin', rejectLogin = false } = {}) {
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
            body = { models: [], active_model: null };
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
            body = { status: 'idle', latest_observation: null, open_incidents: 0 };
        } else if (url.pathname === '/api/diagnostics/incidents') {
            body = { incidents: [], open_incidents: 0 };
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
    page.on('pageerror', error => pageErrors.push(error.message));

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
        '/js/system-monitor.js',
        '/js/ui-preferences.js',
    ]);
    expect(api.requestedPaths()).toEqual(['/api/auth/status']);
    expect(pageErrors).toEqual([]);
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
    await page.locator('[data-panel="diagnostics-panel"]').click();
    await expect(page.locator('#diagnostics-panel')).toBeVisible();
    await expect(page.locator('#diagnostics-run')).toBeVisible();
    await expect(page.locator('#bot-restart')).toBeHidden();
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
