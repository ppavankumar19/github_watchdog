/* app.js — minimal client-side utilities */

// Auto-refresh dashboard status every 30s (only on the index page)
if (window.location.pathname === '/') {
  setInterval(async () => {
    try {
      const res  = await fetch('/api/status');
      const data = await res.json();

      const el = document.getElementById('last-run');
      if (el && data.last_run) {
        el.textContent = data.last_run.replace('T', ' ').replace('Z', ' UTC');
      }

      const nr = document.getElementById('next-run');
      if (nr && data.next_run) {
        nr.textContent = data.next_run.slice(0, 19).replace('T', ' ') + ' UTC';
      }
    } catch (_) { /* silently ignore */ }
  }, 30_000);
}
