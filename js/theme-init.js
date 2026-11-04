try {
    const p = JSON.parse(localStorage.getItem('ai-server-ui-prefs')) || {};
    if (p.theme === 'light') document.documentElement.dataset.theme = 'light';
} catch (e) {}
