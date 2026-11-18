// Own profile + questionnaire. Identity/CSRF come only from /api/session; nothing private is stored.
const form = document.querySelector('[data-profile-form]');
const status = document.querySelector('[data-profile-status]');
const intro = document.querySelector('[data-setup-intro]');
const errorBox = document.querySelector('[data-profile-error]');
const profileFields = ['first_name', 'last_name', 'locale'];
const numberFields = ['birth_year', 'height_cm', 'weight_kg'];
let csrf = null;
let onboardingRevision = 0;
let setupMode = false;

async function json(url, options = {}) {
  const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000), ...options});
  return {response, body: await response.json().catch(() => null)};
}

const groups = () => [...form.querySelectorAll('[data-group]')];
const checked = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value);

// Mirror the API limits in the UI: disable extra choices once the maximum is reached.
function syncLimits() {
  for (const group of groups()) {
    const max = Number(group.dataset.max || 0);
    if (!max) continue;
    const inputs = [...group.querySelectorAll('input')];
    const full = inputs.filter(input => input.checked).length >= max;
    for (const input of inputs) input.disabled = full && !input.checked;
  }
}

function setChoices(name, values) {
  const wanted = new Set((values ?? []).map(String));
  for (const input of form.querySelectorAll(`input[name="${name}"]`)) input.checked = wanted.has(input.value);
}

function fill(profile, onboarding, preferences) {
  for (const name of profileFields) form.elements[name].value = profile[name] || (name === 'locale' ? 'uk' : '');
  form.elements.theme_preference.value = preferences.theme_preference;
  onboardingRevision = onboarding?.revision ?? 0;
  for (const name of ['goal_codes', 'weekdays']) setChoices(name, onboarding?.[name]);
  for (const name of ['self_reported_level', 'time_of_day', 'session_minutes']) setChoices(name, onboarding?.[name] == null ? [] : [onboarding[name]]);
  for (const name of numberFields) form.elements[name].value = onboarding?.[name] ?? '';
  syncLimits();
}

function validate() {
  let first = null;
  const mark = (element, bad) => {
    element.setAttribute('aria-invalid', String(bad));
    if (bad && !first) first = element.matches('[data-group]') ? element.querySelector('input:not(:disabled)') : element;
  };
  for (const name of ['first_name', 'last_name']) mark(form.elements[name], !form.elements[name].value.trim());
  for (const group of groups()) mark(group, checked(group.dataset.group).length < Number(group.dataset.min || 0));
  for (const name of numberFields) mark(form.elements[name], !form.elements[name].checkValidity());
  errorBox.hidden = !first;
  first?.focus();
  return !first;
}

function payload() {
  const number = name => (form.elements[name].value === '' ? null : Number(form.elements[name].value));
  const one = name => checked(name)[0] ?? null;
  return {
    goal_codes: checked('goal_codes'),
    self_reported_level: Number(one('self_reported_level')),
    session_minutes: Number(one('session_minutes')),
    weekdays: checked('weekdays').map(Number).sort((a, b) => a - b),
    time_of_day: one('time_of_day'),
    birth_year: number('birth_year'),
    height_cm: number('height_cm'),
    weight_kg: number('weight_kg'),
    expected_revision: onboardingRevision,
  };
}

async function load() {
  const session = await json('/api/session');
  if (session.response.status === 401 || !session.body?.authenticated) {
    window.location.assign('/login');
    return;
  }
  csrf = session.body.csrf_token;
  const [profile, onboarding, preferences] = await Promise.all(
    ['/api/me/profile', '/api/me/onboarding', '/api/me/preferences'].map(url => json(url)),
  );
  if (![profile, onboarding, preferences].every(result => result.response.ok)) {
    status.textContent = status.dataset.unavailable;
    return;
  }
  setupMode = session.body.setup_required === true;
  if (setupMode) {
    intro.hidden = false;
    const figure = intro.querySelector('[data-handstand-cycle]');
    const motion = await import('/static/js/components/handstand-motion.js');
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) motion.drawPose(figure, 0.55);
    else motion.mountHandstandCycle(figure);
  }
  fill(profile.body, onboarding.body, preferences.body);
  status.textContent = '';
  form.hidden = false;
}

document.addEventListener('studio:account', event => {
  const preference = event.detail?.preference;
  if (form && preference) form.elements.theme_preference.value = preference;
});

form?.addEventListener('change', event => {
  if (event.target.name === 'theme_preference') {
    document.dispatchEvent(new CustomEvent('studio:theme-select', {detail: event.target.value}));
    return;
  }
  syncLimits();
  event.target.closest('[data-group]')?.setAttribute('aria-invalid', 'false');
});

form?.addEventListener('submit', async event => {
  event.preventDefault();
  if (!validate()) return;
  const submit = form.querySelector('[type=submit]');
  const label = submit.textContent;
  submit.disabled = true;
  submit.textContent = submit.dataset.pendingLabel;
  const headers = {'Content-Type': 'application/json', 'X-CSRF-Token': csrf};
  try {
    const profile = await json('/api/me/profile', {
      method: 'PATCH', headers,
      body: JSON.stringify(Object.fromEntries(profileFields.map(name => [name, form.elements[name].value.trim()]))),
    });
    const onboarding = await json('/api/me/onboarding', {method: 'PUT', headers, body: JSON.stringify(payload())});
    if (onboarding.response.status === 409 && onboarding.body?.current) {
      fill(profile.body ?? {}, onboarding.body.current, {theme_preference: form.elements.theme_preference.value});
      status.textContent = status.dataset.conflict;
      return;
    }
    if (!profile.response.ok || !onboarding.response.ok) throw new Error('save failed');
    onboardingRevision = onboarding.body.revision;
    status.textContent = status.dataset.saved;
    if (setupMode) {
      setupMode = false;
      intro.hidden = true;
    }
  } catch {
    status.textContent = status.dataset.error;
  } finally {
    submit.disabled = false;
    if (submit.textContent === submit.dataset.pendingLabel) submit.textContent = label;
  }
});

if (form && status) load().catch(() => { status.textContent = status.dataset.unavailable; });
