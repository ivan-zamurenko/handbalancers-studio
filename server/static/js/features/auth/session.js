import {clearAccountState} from '../../state/session.js';

// Credentials, CSRF and current account identity live only in memory.
const logout = document.querySelector('[data-logout]');
const login = document.querySelector('[data-login-link]');
let csrf = null;
let accountId = null;
let revision = 0;
let logoutPending = false;

function forgetAccount() {
  clearAccountState(accountId);
  accountId = null;
  csrf = null;
}

async function refresh() {
  if (logoutPending || !logout || !login) return;
  const requestRevision = ++revision;
  try {
    const response = await fetch('/api/session', {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000)});
    if (!response.ok && response.status !== 401) throw new Error('Session unavailable');
    const snapshot = response.ok ? await response.json() : {authenticated: false};
    if (requestRevision !== revision) return;
    const authenticated = snapshot.authenticated === true && !!snapshot.csrf_token;
    if (!authenticated || (accountId && accountId !== snapshot.user?.id)) forgetAccount();
    csrf = authenticated ? snapshot.csrf_token : null;
    accountId = authenticated ? snapshot.user?.id || null : null;
    logout.hidden = !authenticated; login.hidden = authenticated;
    logout.disabled = false;
  } catch {
    if (requestRevision !== revision) return;
    // An outage is not proof of logout. Keep the existing session/CSRF retryable.
    logout.disabled = false;
    if (!csrf) { logout.hidden = true; login.hidden = false; }
  }
}

logout?.addEventListener('click', async () => {
  if (!csrf || logout.disabled || logoutPending) return;
  logoutPending = true;
  ++revision; // A snapshot started before logout must not restore old account state.
  logout.disabled = true;
  try {
    const response = await fetch('/api/auth/logout', {method: 'POST', credentials: 'same-origin', headers: {'X-CSRF-Token': csrf}, signal: AbortSignal.timeout(8000)});
    if (response.status === 204) {
      forgetAccount();
      logout.hidden = true; login.hidden = false;
      window.location.assign('/login');
      return;
    }
  } catch {
    // Response loss is ambiguous; reconcile against the server below.
  } finally {
    logoutPending = false;
  }
  await refresh();
});
window.addEventListener('pageshow', refresh);
