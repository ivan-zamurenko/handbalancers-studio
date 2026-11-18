// Own profile + questionnaire. Identity/CSRF come only from /api/session; nothing private is stored.
// Phone: first fill is a step-by-step form; editing later uses collapsible sections.
import {playSaveFeedback} from '../../components/save-feedback.js';

const form = document.querySelector('[data-profile-form]');
const status = document.querySelector('[data-profile-status]');
const intro = document.querySelector('[data-setup-intro]');
const heading = document.querySelector('[data-profile-heading]');
const errorBox = document.querySelector('[data-profile-error]');
const wizardHead = document.querySelector('[data-wizard-head]');
const buttons = {
  back: document.querySelector('[data-wizard-back]'),
  skip: document.querySelector('[data-wizard-skip]'),
  next: document.querySelector('[data-wizard-next]'),
  submit: form?.querySelector('[type=submit]'),
};
const phone = matchMedia('(max-width: 760px)');
const profileFields = ['first_name', 'last_name', 'locale'];
const numberFields = ['birth_year', 'height_cm', 'weight_kg'];
const sections = form ? [...form.querySelectorAll('fieldset[data-step]')] : [];
let csrf = null;
let onboardingRevision = 0;
let setupMode = false;
let mode = 'full';
let stepIndex = 0;
let saving = false;

async function json(url, options = {}) {
  const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000), ...options});
  return {response, body: await response.json().catch(() => null)};
}

const groupsIn = scope => [...scope.querySelectorAll('[data-group]')];
const checked = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value);
const labelOf = input => input.closest('.chip-option')?.querySelector('span')?.textContent.trim() ?? input.value;
const checkedLabels = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(labelOf);

function syncLimits() {
  for (const group of groupsIn(form)) {
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
  if (preferences) form.elements.theme_preference.value = preferences.theme_preference;
  onboardingRevision = onboarding?.revision ?? 0;
  for (const name of ['goal_codes', 'weekdays']) setChoices(name, onboarding?.[name]);
  for (const name of ['self_reported_level', 'time_of_day', 'session_minutes']) setChoices(name, onboarding?.[name] == null ? [] : [onboarding[name]]);
  for (const name of numberFields) form.elements[name].value = onboarding?.[name] ?? '';
  syncLimits();
  updateSummaries();
}

// Validates one section (or the whole form) and focuses the first problem.
function validate(scope = form) {
  let first = null;
  const mark = (element, bad) => {
    element.setAttribute('aria-invalid', String(bad));
    if (bad && !first) first = element.matches('[data-group]') ? element.querySelector('input:not(:disabled)') : element;
  };
  for (const name of ['first_name', 'last_name']) {
    const input = form.elements[name];
    if (scope.contains(input)) mark(input, !input.value.trim());
  }
  for (const group of groupsIn(scope)) mark(group, checked(group.dataset.group).length < Number(group.dataset.min || 0));
  for (const name of numberFields) {
    const input = form.elements[name];
    if (scope.contains(input)) mark(input, !input.checkValidity());
  }
  errorBox.hidden = !first;
  if (first) {
    const section = first.closest('fieldset[data-step]');
    if (mode === 'accordion' && section) setOpen(section, true);
    first.focus();
  }
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

// ---------- Layout modes ----------
function wrapSections() {
  for (const section of sections) {
    if (section.querySelector(':scope > [data-section-body]')) continue;
    const body = document.createElement('div');
    body.dataset.sectionBody = '';
    body.id = `profile-section-${section.dataset.step}`;
    for (const node of [...section.childNodes]) if (node.nodeName !== 'LEGEND') body.append(node);
    section.append(body);
    const legend = section.querySelector('legend');
    legend.tabIndex = -1;
    const title = legend.textContent.trim();
    legend.textContent = '';
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'acc-toggle';
    toggle.dataset.accToggle = '';
    toggle.setAttribute('aria-controls', body.id);
    toggle.innerHTML = '<span class="acc-title"></span><span class="acc-summary" data-acc-summary></span><svg class="acc-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>';
    toggle.querySelector('.acc-title').textContent = title;
    toggle.addEventListener('click', () => { if (mode === 'accordion') setOpen(section, section.dataset.open !== 'true'); });
    legend.append(toggle);
  }
}

function setOpen(section, open) {
  section.dataset.open = String(open);
  section.querySelector('[data-acc-toggle]')?.setAttribute('aria-expanded', String(open));
}

function updateSummaries() {
  const uk = document.documentElement.lang !== 'en';
  const text = {
    about: [form.elements.first_name.value, form.elements.last_name.value].filter(Boolean).join(' '),
    goals: [...checkedLabels('goal_codes'), ...checkedLabels('self_reported_level')].join(' · '),
    schedule: [checkedLabels('weekdays').join(', '), ...checkedLabels('time_of_day'), ...checkedLabels('session_minutes')].filter(Boolean).join(' · '),
    body: [form.elements.birth_year.value, form.elements.height_cm.value && `${form.elements.height_cm.value} ${uk ? 'см' : 'cm'}`,
      form.elements.weight_kg.value && `${uk ? form.elements.weight_kg.value.replace('.', ',') : form.elements.weight_kg.value} ${uk ? 'кг' : 'kg'}`].filter(Boolean).join(' · '),
    settings: [form.elements.locale.selectedOptions[0]?.textContent, form.elements.theme_preference.selectedOptions[0]?.textContent].join(' · '),
  };
  for (const section of sections) {
    const summary = section.querySelector('[data-acc-summary]');
    if (summary) summary.textContent = text[section.dataset.step] || '—';
  }
}

const wizardSteps = () => sections.filter(section => !section.hasAttribute('data-setup-skip'));

function showStep(index, {focus = true} = {}) {
  const steps = wizardSteps();
  stepIndex = Math.max(0, Math.min(index, steps.length - 1));
  for (const section of sections) section.hidden = section !== steps[stepIndex];
  const last = stepIndex === steps.length - 1;
  const counter = wizardHead.querySelector('[data-wizard-count]');
  counter.textContent = status.dataset.stepLabel.replace('{n}', stepIndex + 1).replace('{total}', steps.length);
  wizardHead.querySelector('[data-wizard-bar]').style.width = `${((stepIndex + 1) / steps.length) * 100}%`;
  buttons.back.hidden = stepIndex === 0;
  buttons.next.hidden = last;
  buttons.submit.hidden = !last;
  buttons.skip.hidden = !(last && steps[stepIndex].hasAttribute('data-optional'));
  // The welcome text belongs to the first step only; later steps need the space.
  intro.hidden = stepIndex !== 0;
  errorBox.hidden = true;
  if (focus) {
    window.scrollTo({top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    steps[stepIndex].querySelector('legend')?.focus({preventScroll: true});
  }
}

function applyMode() {
  const next = phone.matches ? (setupMode ? 'wizard' : 'accordion') : 'full';
  mode = next;
  form.dataset.mode = mode;
  for (const section of sections) {
    const toggle = section.querySelector('[data-acc-toggle]');
    toggle.disabled = mode !== 'accordion';
    if (mode !== 'accordion') toggle.removeAttribute('aria-expanded');
  }
  wizardHead.hidden = mode !== 'wizard';
  if (mode === 'wizard') {
    showStep(stepIndex, {focus: false});
    return;
  }
  for (const section of sections) section.hidden = false;
  for (const button of [buttons.back, buttons.next, buttons.skip]) button.hidden = true;
  buttons.submit.hidden = false;
  sections.forEach((section, index) => setOpen(section, mode === 'full' || index === 0));
}

// ---------- Load & save ----------
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
  intro.hidden = !setupMode;
  heading.hidden = setupMode;
  wrapSections();
  fill(profile.body, onboarding.body, preferences.body);
  applyMode();
  status.textContent = '';
  form.hidden = false;
}

async function save() {
  const headers = {'Content-Type': 'application/json', 'X-CSRF-Token': csrf};
  const profile = await json('/api/me/profile', {
    method: 'PATCH', headers,
    body: JSON.stringify(Object.fromEntries(profileFields.map(name => [name, form.elements[name].value.trim()]))),
  });
  const onboarding = await json('/api/me/onboarding', {method: 'PUT', headers, body: JSON.stringify(payload())});
  if (onboarding.response.status === 409 && onboarding.body?.current) return {kind: 'conflict', profile, onboarding};
  if (!profile.response.ok || !onboarding.response.ok) return {kind: 'error'};
  return {kind: 'ok', onboarding};
}

form?.addEventListener('change', event => {
  if (event.target.name === 'theme_preference') {
    document.dispatchEvent(new CustomEvent('studio:theme-select', {detail: event.target.value}));
  } else {
    syncLimits();
    event.target.closest('[data-group]')?.setAttribute('aria-invalid', 'false');
  }
  updateSummaries();
});
form?.addEventListener('input', updateSummaries);

buttons.next?.addEventListener('click', () => {
  if (validate(wizardSteps()[stepIndex])) showStep(stepIndex + 1);
});
buttons.back?.addEventListener('click', () => showStep(stepIndex - 1));
buttons.skip?.addEventListener('click', () => {
  for (const name of numberFields) form.elements[name].value = '';
  form.requestSubmit();
});
// Enter in a text field moves to the next step instead of submitting early.
form?.addEventListener('keydown', event => {
  if (mode === 'wizard' && event.key === 'Enter' && event.target.matches('input:not([type=checkbox]):not([type=radio])') && !buttons.next.hidden) {
    event.preventDefault();
    buttons.next.click();
  }
});

form?.addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  if (!validate()) return;
  saving = true;
  buttons.submit.disabled = true;
  const submitLabel = buttons.submit.textContent;
  buttons.submit.textContent = document.documentElement.lang === 'en' ? 'Saving…' : 'Зберігаємо…';
  form.setAttribute('aria-busy', 'true');
  const request = save().catch(() => ({kind: 'error'}));
  const variant = setupMode ? 'full' : 'short';
  await playSaveFeedback({
    request: request.then(result => result.kind === 'ok'),
    variant,
    form,
    labels: {saved: status.dataset.feedbackSaved, error: status.dataset.feedbackError},
  });
  const result = await request;
  buttons.submit.disabled = false;
  buttons.submit.textContent = submitLabel;
  form.removeAttribute('aria-busy');
  saving = false;
  if (result.kind === 'ok') {
    onboardingRevision = result.onboarding.body.revision;
    status.textContent = '';
    if (setupMode) {
      setupMode = false;
      intro.hidden = true;
      heading.hidden = false;
      applyMode();
      window.scrollTo({top: 0});
    }
  } else if (result.kind === 'conflict') {
    fill(result.profile.body ?? {}, result.onboarding.body.current, null);
    status.textContent = status.dataset.conflict;
  } else {
    status.textContent = status.dataset.error;
  }
  buttons.submit.focus({preventScroll: true});
});

document.addEventListener('studio:account', event => {
  const preference = event.detail?.preference;
  if (form && preference) form.elements.theme_preference.value = preference;
});

phone.addEventListener('change', () => { if (!form.hidden) applyMode(); });

if (form && status) load().catch(() => { status.textContent = status.dataset.unavailable; });
