import {beginLoading, beginNavigation} from '../../components/loading.js';

// UI preview only. Real submission requires the server session and CSRF flow.
const form = document.getElementById('login-form');
form?.addEventListener('submit', event => event.preventDefault());
const password = document.getElementById('login-password');
const toggle = document.querySelector('[data-password-toggle]');
if (password && toggle) {
  toggle.disabled = false;
  toggle.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(visible));
    toggle.setAttribute('aria-label', visible ? toggle.dataset.hide : toggle.dataset.show);
  });
}
for (const control of document.querySelectorAll('[data-login-interactive]')) control.disabled = false;
// A browser history entry must not keep the preview password visible or populated.
window.addEventListener('pagehide', () => {
  if (password) { password.value = ''; password.type = 'password'; }
  if (toggle) { toggle.setAttribute('aria-pressed', 'false'); toggle.setAttribute('aria-label', toggle.dataset.show); }
});


const providers = [...document.querySelectorAll('[data-oauth-provider]')];
const message = document.getElementById('oauth-message');
let starting = false;
for (const button of providers) {
  button.disabled = false;
  button.addEventListener('click', async () => {
    if (starting) return;
    starting = true;
    for (const control of providers) control.disabled = true;
    message.textContent = message.dataset.pending;
    const finishLoading = beginLoading();
    try {
      const response = await fetch(`/api/auth/oauth/${button.dataset.oauthProvider}/start`, {
        method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({return_to: '/plans'}), signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) throw new Error('Unavailable');
      const result = await response.json();
      const target = new URL(result.authorization_url);
      if (!['https:', 'http:'].includes(target.protocol)) throw new Error('Invalid destination');
      beginNavigation();
      window.location.assign(target.href);
    } catch {
      starting = false;
      message.textContent = message.dataset.error;
      for (const control of providers) control.disabled = false;
    } finally {
      finishLoading();
    }
  });
}
window.addEventListener('pageshow', () => {
  starting = false;
  for (const control of providers) control.disabled = false;
  if (message) message.textContent = '';
});
