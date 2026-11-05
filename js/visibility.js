// Runs `callback` every `intervalMs` while the tab is visible, and once as soon
// as the tab becomes visible again so hidden tabs stop polling the backend.
export function setVisibleInterval(callback, intervalMs) {
    setInterval(() => {
        if (!document.hidden) callback();
    }, intervalMs);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) callback();
    });
}
