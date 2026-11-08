import {requestApi, ApiError} from '../../api/client.js';

const requestForm = document.getElementById('recovery-form');
const confirmForm = document.getElementById('recovery-confirm');
const email = document.getElementById('recovery-email');
const code = document.getElementById('recovery-code');
const password = document.getElementById('recovery-password');
const status = document.getElementById('recovery-status');
const again = document.querySelector('[data-recovery-again]');
let pending = false;
let sentTo = '';
let revision = 0;

function controls(disabled) {
  for (const button of document.querySelectorAll('.login-card button')) button.disabled = disabled;
}
controls(false);

async function submit(event, confirming) {
  event.preventDefault();
  if (pending) return;
  pending = true;
  const current = ++revision;
  controls(true);
  event.target.setAttribute('aria-busy', 'true');
  status.textContent = status.dataset.pending;
  const address = confirming ? sentTo : email.value.trim();
  try {
    await requestApi(`/api/auth/recovery/${confirming ? 'confirm' : 'request'}`, {
      method: 'POST', signal: AbortSignal.timeout(30000),
      body: confirming ? {email: address, token: code.value, password: password.value} : {email: address},
    });
    if (current !== revision) return;
    requestForm.hidden = true;
    confirmForm.hidden = confirming;
    status.textContent = confirming ? status.dataset.done : status.dataset.sent;
    if (confirming) {
      code.value = ''; password.value = ''; sentTo = ''; status.focus();
      window.dispatchEvent(new Event('studio:session-changed'));
    }
    else { sentTo = address; code.focus(); }
  } catch (error) {
    if (current !== revision) return;
    status.textContent = error instanceof ApiError && error.status === 429 ? status.dataset.limited
      : error instanceof ApiError && error.status === 422 ? status.dataset.invalid : status.dataset.error;
    status.focus();
  } finally {
    if (current === revision) { pending = false; controls(false); event.target.removeAttribute('aria-busy'); }
  }
}
requestForm.addEventListener('submit', event => submit(event, false));
confirmForm.addEventListener('submit', event => submit(event, true));
again.addEventListener('click', () => {
  if (pending) return;
  sentTo = ''; code.value = ''; password.value = '';
  confirmForm.hidden = true; requestForm.hidden = false; status.textContent = ''; email.focus();
});
window.addEventListener('pagehide', () => {
  ++revision; pending = false; sentTo = ''; code.value = ''; password.value = ''; email.value = '';
  requestForm.hidden = false; confirmForm.hidden = true; status.textContent = '';
  requestForm.removeAttribute('aria-busy'); confirmForm.removeAttribute('aria-busy'); controls(false);
});
