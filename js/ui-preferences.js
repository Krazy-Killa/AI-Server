export function initializeUiPreferences() {
    const swatches = document.querySelectorAll('.swatch');
    const root = document.documentElement;
    const appEl = document.querySelector('.app');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const themeToggle = document.getElementById('theme-toggle');
    const themeLabel = document.getElementById('theme-label');
    const saveConfigButton = document.getElementById('save-config');

    const PREFS_KEY = 'ai-server-ui-prefs';
    const ACCENTS = {
        blue: '74, 140, 255',
        green: '66, 245, 197',
        purple: '180, 106, 255',
        orange: '255, 154, 74',
    };

    function loadPrefs() {
        try {
            return JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
        } catch (error) {
            return {};
        }
    }

    const prefs = Object.assign({ theme: 'dark', accent: 'green', sidebarCollapsed: false }, loadPrefs());

    function savePrefs() {
        try {
            localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
        } catch (error) {
            console.warn('Could not persist UI preferences', error);
        }
    }

    function applyTheme(theme) {
        prefs.theme = theme === 'light' ? 'light' : 'dark';
        root.dataset.theme = prefs.theme;
        if (themeLabel) themeLabel.textContent = prefs.theme === 'light' ? 'Light / Daylight' : 'Dark / Command';
        if (themeToggle) themeToggle.textContent = prefs.theme === 'light' ? 'Switch to dark' : 'Switch to light';
    }

    function applyAccent(name) {
        const rgb = ACCENTS[name] || ACCENTS.green;
        prefs.accent = ACCENTS[name] ? name : 'green';
        root.style.setProperty('--accent-rgb', rgb);
        root.style.setProperty('--accent', `rgb(${rgb})`);
        swatches.forEach(swatch => {
            const active = swatch.classList.contains(prefs.accent);
            swatch.classList.toggle('active', active);
            swatch.setAttribute('aria-pressed', String(active));
        });
    }

    function applySidebar(collapsed) {
        prefs.sidebarCollapsed = Boolean(collapsed);
        appEl.classList.toggle('sidebar-collapsed', prefs.sidebarCollapsed);
        if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', String(!prefs.sidebarCollapsed));
    }

    swatches.forEach(swatch => {
        swatch.addEventListener('click', () => {
            applyAccent(Object.keys(ACCENTS).find(name => swatch.classList.contains(name)));
            savePrefs();
        });
    });

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            applyTheme(prefs.theme === 'light' ? 'dark' : 'light');
            savePrefs();
        });
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            applySidebar(!prefs.sidebarCollapsed);
            savePrefs();
        });
    }

    if (saveConfigButton) {
        saveConfigButton.addEventListener('click', () => {
            savePrefs();
            saveConfigButton.textContent = 'Saved ✓';
            setTimeout(() => { saveConfigButton.textContent = 'Save Configuration'; }, 1500);
        });
    }

    applyTheme(prefs.theme);
    applyAccent(prefs.accent);
    applySidebar(prefs.sidebarCollapsed);
    initializeSettingsTabs();
}

function initializeSettingsTabs() {
    const tabs = Array.from(document.querySelectorAll('.settings-tab'));
    const views = document.querySelectorAll('.settings-view');
    const origin = document.getElementById('settings-origin');
    const connection = document.getElementById('settings-connection');

    function selectTab(name, { focus = false } = {}) {
        tabs.forEach(tab => {
            const active = tab.dataset.settingsTab === name;
            tab.classList.toggle('active', active);
            tab.setAttribute('aria-selected', String(active));
            tab.tabIndex = active ? 0 : -1;
            if (active && focus) tab.focus();
        });
        views.forEach(view => {
            view.hidden = view.id !== `settings-view-${name}`;
        });
    }

    tabs.forEach(tab => {
        tab.addEventListener('click', () => selectTab(tab.dataset.settingsTab));
        tab.addEventListener('keydown', event => {
            const visible = tabs.filter(candidate => !candidate.hidden);
            const index = visible.indexOf(tab);
            const target = {
                ArrowRight: visible[(index + 1) % visible.length],
                ArrowLeft: visible[(index - 1 + visible.length) % visible.length],
                Home: visible[0],
                End: visible[visible.length - 1],
            }[event.key];
            if (!target) return;
            event.preventDefault();
            selectTab(target.dataset.settingsTab, { focus: true });
        });
    });

    document.querySelectorAll('[data-settings-goto]').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelector(`[data-panel="${button.dataset.settingsGoto}"]`)?.click();
        });
    });

    if (origin) origin.textContent = window.location.origin;
    if (connection) {
        connection.textContent = window.location.protocol === 'https:'
            ? 'Encrypted (HTTPS)'
            : 'Not encrypted (HTTP) — acceptable only on this machine';
    }

    document.addEventListener('settings:reset-tab', () => selectTab('appearance'));
}
