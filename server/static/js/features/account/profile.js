// Own profile editor. Identity and CSRF come only from /api/session; nothing private is stored.
const form = document.querySelector('[data-profile-form]');
const status = document.querySelector('[data-profile-status]');
const fields = ['first_name', 'last_name', 'locale'];
let csrf = null;

async function json(url, options = {}) {
  const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000), ...options});
  return {response, body: await response.json().catch(() => null)};
}

async function load() {
  const session = await json('/api/session');
  if (session.response.status === 401 || !session.body?.authenticated) {
    window.location.assign('/login');
    return;
  }
  csrf = session.body.csrf_token;
  const [profile, preferences] = await Promise.all([json('/api/me/profile'), json('/api/me/preferences')]);
  if (!profile.response.ok || !preferences.response.ok) {
    status.textContent = status.dataset.unavailable;
    return;
  }
  for (const name of fields) form.elements[name].value = profile.body[name] || (name === 'locale' ? 'uk' : '');
  form.elements.theme_preference.value = preferences.body.theme_preference;
  status.textContent = '';
  form.hidden = false;
}

// Keep the select in sync when another device's value is adopted.
document.addEventListener('studio:account', event => {
  const preference = event.detail?.preference;
  if (form && preference) form.elements.theme_preference.value = preference;
});

form?.elements.theme_preference.addEventListener('change', event => {
  // Apply now; session.js persists it with the revision it holds.
  document.dispatchEvent(new CustomEvent('studio:theme-select', {detail: event.target.value}));
});

form?.addEventListener('submit', async event => {
  event.preventDefault();
  const submit = form.querySelector('[type=submit]');
  const label = submit.textContent;
  submit.disabled = true;
  submit.textContent = submit.dataset.pendingLabel;
  const changes = Object.fromEntries(fields.map(name => [name, form.elements[name].value.trim()]));
  try {
    const result = await json('/api/me/profile', {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
      body: JSON.stringify(changes),
    });
    status.textContent = result.response.ok ? status.dataset.saved : status.dataset.error;
  } catch {
    status.textContent = status.dataset.error;
  } finally {
    submit.disabled = false;
    submit.textContent = label;
  }
});

if (form && status) load().catch(() => { status.textContent = status.dataset.unavailable; });
