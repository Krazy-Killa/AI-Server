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
}
