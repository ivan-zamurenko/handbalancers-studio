import {clearAccountState} from '../../state/session.js';
import {beginLoading, beginNavigation} from '../../components/loading.js';
import {claimGuestDraft} from '../onboarding/draft.js';

// Credentials, CSRF and current account identity live only in memory.
const logout = document.querySelector('[data-logout]');
const login = document.querySelector('[data-login-link]');
const profileLink = document.querySelector('[data-profile-link]');
const loginCta = document.querySelector('[data-login-cta]');
let csrf = null;
let accountId = null;
let revision = 0;
let logoutPending = false;
let themeRevision = null;
let themeInFlight = false;
let themeWanted = null;

function announceAccount(id, preference) {
  document.dispatchEvent(new CustomEvent('studio:account', {detail: {id, preference}}));
}

function forgetAccount() {
  const hadAccount = !!accountId;
  clearAccountState(accountId);
  accountId = null;
  csrf = null;
  themeRevision = null;
  themeWanted = null;
  if (hadAccount) announceAccount(null);
}

async function loadServerTheme(id) {
  let current = null;
  try {
    const response = await fetch('/api/me/preferences', {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000)});
    if (response.ok) current = await response.json();
  } catch {
    // Server preference is optional for rendering; keep the account-local value.
  }
  // A late answer for a signed-out or replaced account must not re-attach its storage.
  if (accountId !== id) return;
  if (current) themeRevision = current.revision;
  announceAccount(id, current?.theme_preference);
}

// One PATCH at a time; the latest local choice is sent after the previous one settles.
async function saveServerTheme(preference) {
  themeWanted = preference;
  if (themeInFlight) return;
  themeInFlight = true;
  try {
    while (themeWanted !== null && accountId && csrf && themeRevision !== null) {
      const id = accountId;
      const sending = themeWanted;
      themeWanted = null;
      const response = await fetch('/api/me/preferences', {
        method: 'PATCH', credentials: 'same-origin', signal: AbortSignal.timeout(8000),
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({theme_preference: sending, expected_revision: themeRevision}),
      }).catch(() => null);
      if (!response || accountId !== id) return;
      const body = await response.json().catch(() => null);
      if (response.ok && body) themeRevision = body.revision;
      else if (response.status === 409 && body?.current) {
        themeRevision = body.current.revision;
        // Another device won. Keep a newer local choice (retried next loop), else adopt.
        if (themeWanted === null) announceAccount(id, body.current.theme_preference);
      } else return;
    }
  } finally {
    themeInFlight = false;
  }
}

// Completion is server-owned. A per-tab "offered" flag must never bypass setup.
const setupExempt = new Set(['/profile', '/onboarding', '/login', '/register', '/verify-email', '/recovery']);
function offerSetup() {
  if (setupExempt.has(window.location.pathname)) return;
  beginNavigation();
  window.location.assign(`/profile?lang=${document.documentElement.lang || 'uk'}`);
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
    const previous = accountId;
    accountId = authenticated ? snapshot.user?.id || null : null;
    if (accountId && accountId !== previous) loadServerTheme(accountId);
    if (authenticated) claimGuestDraft(accountId);
    if (authenticated && window.location.pathname === '/onboarding') {
      window.location.replace(`/dashboard?lang=${document.documentElement.lang || 'uk'}`);
    } else if (authenticated && snapshot.setup_required === true) offerSetup();
    logout.hidden = !authenticated; login.hidden = authenticated;
    if (profileLink) profileLink.hidden = !authenticated;
    if (loginCta) loginCta.hidden = authenticated;
    logout.disabled = false;
  } catch {
    if (requestRevision !== revision) return;
    // An outage is not proof of logout. Keep the existing session/CSRF retryable.
    logout.disabled = false;
    if (!csrf) { logout.hidden = true; login.hidden = false; if (profileLink) profileLink.hidden = true; if (loginCta) loginCta.hidden = false; }
  }
}

logout?.addEventListener('click', async () => {
  if (!csrf || logout.disabled || logoutPending) return;
  logoutPending = true;
  ++revision; // A snapshot started before logout must not restore old account state.
  logout.disabled = true;
  const finishLoading = beginLoading({mode:'button', target:logout});
  try {
    const response = await fetch('/api/auth/logout', {method: 'POST', credentials: 'same-origin', headers: {'X-CSRF-Token': csrf}, signal: AbortSignal.timeout(8000)});
    if (response.status === 204) {
      forgetAccount();
      logout.hidden = true; login.hidden = false;
      if (profileLink) profileLink.hidden = true;
      if (loginCta) loginCta.hidden = false;
      beginNavigation();
      window.location.assign('/login');
      return;
    }
  } catch {
    // Response loss is ambiguous; reconcile against the server below.
  } finally {
    logoutPending = false;
    finishLoading();
  }
  await refresh();
});
window.addEventListener('pageshow', refresh);
window.addEventListener('studio:session-changed', refresh);
document.addEventListener('studio:theme-changed', event => saveServerTheme(event.detail));
