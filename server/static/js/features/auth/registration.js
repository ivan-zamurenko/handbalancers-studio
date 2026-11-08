import {requestApi, ApiError} from '../../api/client.js';
import {beginLoading, beginNavigation} from '../../components/loading.js';

const form = document.querySelector('[data-auth-form]');
const action = form?.dataset.authForm;
const enabled = form?.dataset.authEnabled === 'true';
const field = name => form?.querySelector(`[data-auth-field="${name}"]`);
const status = document.querySelector('[data-auth-status]');
const submit = form?.querySelector('[data-auth-submit]');
const resend = form?.querySelector('[data-auth-resend]');
const providers = [...document.querySelectorAll('[data-oauth-provider]')];
const oauthMessage = document.getElementById('oauth-message');
const toggles = [...document.querySelectorAll('[data-password-toggle]')];
const draftKey = 'studio:auth-draft';
const language = document.documentElement.lang === 'en' ? 'en' : 'uk';
let pending = null, navigating = false, completed = false;
let resendUntil = 0, retryUntil = 0, timer;

function readDraft() {
  try {
    const value = JSON.parse(sessionStorage.getItem(draftKey));
    if (value && typeof value === 'object' && value.expires_at > Date.now() && value.expires_at <= Date.now()+1800000) return value;
    sessionStorage.removeItem(draftKey);
  } catch { /* Storage may be disabled. The email field remains editable. */ }
  return {};
}
function saveDraft() {
  if (completed) return;
  const draft = {expires_at:Date.now()+1800000};
  // Explicit allowlist: never serialize a form or save password/OTP/provider data.
  const previous = readDraft();
  for (const name of ['first_name','last_name','email']) {
    const value = field(name)?.value ?? previous[name];
    if (typeof value === 'string') draft[name] = value.slice(0,name==='email'?254:100);
  }
  draft.resend_until = resendUntil;
  try {sessionStorage.setItem(draftKey,JSON.stringify(draft));} catch { /* Optional convenience. */ }
}
function clearSecrets() {
  for (const name of ['password','token']) if (field(name)) field(name).value = '';
  if (field('password')) field('password').type = 'password';
  for (const toggle of toggles) {
    toggle.setAttribute('aria-pressed','false');
    toggle.setAttribute('aria-label',toggle.dataset.show);
  }
}
function syncControls() {
  const busy = Boolean(pending) || navigating;
  if (submit) submit.disabled = busy || !enabled || Date.now() < retryUntil;
  for (const input of form?.querySelectorAll('input') ?? []) input.disabled = busy;
  for (const button of [...providers,...toggles]) button.disabled = busy;
  if (resend) {
    const seconds = Math.max(0,Math.ceil((resendUntil-Date.now())/1000));
    resend.disabled = busy || !enabled || seconds>0;
    if (!busy) resend.textContent = seconds ? `${resend.dataset.wait} ${seconds} ${language==='en'?'s':'с'}` : resend.dataset.label;
  }
}
function startTimer() {
  clearInterval(timer);
  timer = setInterval(syncControls,1000);
}
function showError(error) {
  const code = error instanceof ApiError ? error.status : 0;
  status.textContent = code===429 ? status.dataset.limited : [401,422].includes(code) ? status.dataset.invalid : status.dataset.error;
  status.focus({preventScroll:true});
}
function startAttempt() {
  if (pending || navigating) return null;
  pending = new AbortController();
  syncControls();
  return pending;
}
function go(path) {
  navigating = true;
  syncControls();
  beginNavigation();
  location.assign(`${path}?lang=${language}`);
}

const draft = readDraft();
for (const name of ['first_name','last_name','email']) {
  if (field(name) && typeof draft[name] === 'string') field(name).value = draft[name].slice(0,name==='email'?254:100);
}
if (typeof draft.resend_until === 'number' && draft.resend_until <= Date.now()+60000) resendUntil = draft.resend_until;
clearSecrets();
form?.addEventListener('input', event => {
  if (event.target === field('email')) {
    if (field('token')) field('token').value = '';
    // Keep the existing cooldown when editing; the server remains authoritative.
  }
  saveDraft();
  syncControls();
});

async function send(event, resending=false) {
  event.preventDefault();
  if (!enabled || pending || navigating || Date.now() < (resending?resendUntil:retryUntil)) return;
  if (resending ? !field('email').reportValidity() : !form.reportValidity()) return;
  const body = {email:field('email').value.trim()};
  if (!resending) {
    if (action==='register') for (const name of ['first_name','last_name']) body[name] = field(name).value.trim();
    if (field('password')) body.password = field('password').value; // Never trim a password.
    if (field('token')) body.token = field('token').value;
  }
  saveDraft();
  const current = startAttempt();
  form.setAttribute('aria-busy','true');
  status.textContent = '';
  if (oauthMessage) oauthMessage.textContent = '';
  const endpoint = resending ? 'resend-verification' : action==='verify' ? 'verify-email' : action;
  try {
    const result = await requestApi(`/api/auth/${endpoint}`,{
      method:'POST',body,signal:AbortSignal.any([current.signal,AbortSignal.timeout(15000)]),
      loading:{mode:'button',target:resending?resend:submit},
    });
    if (pending !== current) return;
    if (resending) {
      resendUntil = Date.now()+60000;
      saveDraft();
      field('token').value = '';
      status.textContent = status.dataset.sent;
      status.focus({preventScroll:true});
    } else if (action==='register') {
      if (result?.state !== 'verification_pending') throw new Error('Unexpected response');
      clearSecrets();
      resendUntil = Date.now()+60000;
      saveDraft();
      go('/verify-email');
    } else {
      if (result?.state !== 'authenticated') throw new Error('Unexpected response');
      completed = true;
      clearSecrets();
      try {sessionStorage.removeItem(draftKey);} catch { /* Optional storage. */ }
      window.dispatchEvent(new Event('studio:session-changed'));
      go('/plans');
    }
  } catch (error) {
    if (pending !== current) return;
    navigating = false;
    if (error instanceof ApiError && error.status===429) {
      if (resending) {resendUntil=Date.now()+60000;saveDraft();}
      else retryUntil=Date.now()+60000;
    }
    showError(error);
  } finally {
    if (pending===current) {
      pending=null;
      form.removeAttribute('aria-busy');
      syncControls();
    }
  }
}
form?.addEventListener('submit',event=>send(event));
resend?.addEventListener('click',event=>send(event,true));
for (const toggle of toggles) toggle.addEventListener('click',()=>{
  const password = document.getElementById(toggle.getAttribute('aria-controls'));
  const visible = password.type==='password';
  password.type = visible?'text':'password';
  toggle.setAttribute('aria-pressed',String(visible));
  toggle.setAttribute('aria-label',visible?toggle.dataset.hide:toggle.dataset.show);
});

for (const button of providers) button.addEventListener('click',async()=>{
  const current = startAttempt();
  if (!current) return;
  clearSecrets();
  if (status) status.textContent = '';
  oauthMessage.textContent = oauthMessage.dataset.pending;
  const finish = beginLoading({mode:'button',target:button});
  try {
    const result = await requestApi(`/api/auth/oauth/${button.dataset.oauthProvider}/start`,{
      method:'POST',body:{return_to:'/plans'},
      signal:AbortSignal.any([current.signal,AbortSignal.timeout(8000)]),
    });
    if (pending!==current) return;
    const destination = new URL(result.authorization_url);
    if (!['https:','http:'].includes(destination.protocol)) throw new Error('Invalid destination');
    navigating=true;beginNavigation();location.assign(destination.href);
  } catch {
    if (pending!==current) return;
    navigating=false;
    oauthMessage.textContent=oauthMessage.dataset.error;
    oauthMessage.focus({preventScroll:true});
  } finally {
    finish();
    if (pending===current) {pending=null;syncControls();}
  }
});
window.addEventListener('pagehide',()=>{
  saveDraft();clearSecrets();
  pending?.abort();pending=null;navigating=false;
  clearInterval(timer);
  form?.removeAttribute('aria-busy');
  if (status) status.textContent='';
  if (oauthMessage) oauthMessage.textContent='';
  syncControls();
});
window.addEventListener('pageshow',event=>{
  if (event.persisted) {clearSecrets();syncControls();startTimer();}
});
syncControls();startTimer();
