// Keep credentials/CSRF only in memory; no tokens in browser storage.
const logout = document.querySelector('[data-logout]');
const login = document.querySelector('[data-login-link]');
const status = document.querySelector('[data-auth-status]');
let csrf = null;
async function refresh() {
  try {
    const response = await fetch('/api/session', {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000)});
    const snapshot = response.ok ? await response.json() : {authenticated: false};
    csrf = snapshot.csrf_token || null;
    const authenticated = snapshot.authenticated === true && !!csrf;
    logout.hidden = !authenticated; status.hidden = !authenticated; login.hidden = authenticated;
    logout.disabled = false;
  } catch {
    csrf = null; logout.hidden = true; status.hidden = true; login.hidden = false;
  }
}
logout?.addEventListener('click', async () => {
  if (!csrf || logout.disabled) return;
  logout.disabled = true;
  try {
    const response = await fetch('/api/auth/logout', {method: 'POST', credentials: 'same-origin', headers: {'X-CSRF-Token': csrf}, signal: AbortSignal.timeout(8000)});
    if (response.ok) window.location.assign('/login');
    else await refresh();
  } catch { await refresh(); }
});
window.addEventListener('pageshow', refresh);
