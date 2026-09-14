import { memberCopy } from './member-copy.js?v=20260914-membership';
import { copy, goalIds, planIds } from './copy.js?v=20260914-membership';
import { shell, footer, view, isActive } from './views.js?v=20260914-membership';

const STORAGE = { draft: 'hbs:onboarding:v1', locale: 'hbs:locale:v1', plan: 'hbs:plan:v1' };
const read = (key) => {
  try {
    return JSON.parse(localStorage.getItem(key));
  } catch {
    return null;
  }
};
const write = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* The server remains the source of truth when browser storage is unavailable. */
  }
};
const remove = (key) => {
  try {
    localStorage.removeItem(key);
  } catch {
    /* Private browsing can disable storage. */
  }
};
const deviceTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
};
const blankDraft = () => ({
  goals: [],
  experience: '',
  days: [],
  minutes: null,
  minutes_plus: false,
  timezone: deviceTimezone(),
  locale: 'uk',
});
const uniqueAllowed = (values, allowed) =>
  Array.isArray(values) ? [...new Set(values.filter((v) => allowed.includes(v)))] : [];

// Stored browser data is untrusted. Only known document fields reach the API.
function normaliseDraft(value) {
  const d = blankDraft();
  if (!value || typeof value !== 'object') return d;
  d.goals = uniqueAllowed(value.goals, goalIds);
  d.experience = ['beginner', 'intermediate', 'advanced'].includes(value.experience)
    ? value.experience
    : '';
  d.days = uniqueAllowed(value.days, [0, 1, 2, 3, 4, 5, 6]).sort((a, b) => a - b);
  d.minutes = [30, 45, 60, 90].includes(value.minutes) ? value.minutes : null;
  d.minutes_plus = d.minutes === 60 && value.minutes_plus === true;
  // Timezone is device-derived; a corrupt local draft must not make the form unsaveable.
  try {
    if (typeof value.timezone === 'string' && value.timezone.length <= 100) {
      new Intl.DateTimeFormat('en', { timeZone: value.timezone }).format();
      d.timezone = value.timezone;
    }
  } catch {
    /* Retain the device timezone. */
  }
  d.locale = value.locale === 'en' ? 'en' : 'uk';
  return d;
}

const storedLocale = read(STORAGE.locale);
const state = {
  locale: storedLocale === 'en' ? 'en' : 'uk',
  session: null,
  plans: [],
  draft: blankDraft(),
  formStep: 0,
  selectedPlan: planIds.includes(read(STORAGE.plan)) ? read(STORAGE.plan) : 'plus',
  menuOpen: false,
  busy: false,
  error: '',
  fatal: false,
  previewName: '',
  authStage: 'register',
  registration: {},
};
const main = document.querySelector('#main');
const shellElement = document.querySelector('#shell');

function announce(message) {
  document.querySelector('#announcer').textContent = message;
}
function saveDraft(dirty = true) {
  write(STORAGE.draft, { document: state.draft, dirty, owner: state.session?.user?.id || null });
}

class RequestError extends Error {
  constructor(status) {
    super('Request failed');
    this.status = status;
  }
}

async function api(path, body, method) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    headers['X-CSRF-Token'] = state.session.csrf_token;
  }
  const response = await fetch(path, {
    method: method || (body === undefined ? 'GET' : 'POST'),
    credentials: 'same-origin',
    redirect: 'error',
    headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) throw new RequestError(response.status);
  return response.json();
}

function errorText(error) {
  return copy[state.locale][
    error.status === 403
      ? 'sessionError'
      : error instanceof RequestError
        ? 'requestError'
        : 'networkError'
  ];
}

function focusHeading() {
  const heading = main.querySelector('h1');
  if (heading) {
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }
}

let changeObserver;
function observeChangeIllustration() {
  // Disconnect on rerender so route and language changes do not retain old nodes.
  changeObserver?.disconnect();
  const card = main.querySelector('.change-after');
  if (!card || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  changeObserver = new IntersectionObserver(
    ([entry], observer) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.disconnect();
    },
    { threshold: 0.25 },
  );
  changeObserver.observe(card);
}

function render({ focus = false, preserve = false } = {}) {
  // Recheck access after session refreshes as well as navigation.
  guard();
  const activeElement = preserve ? document.activeElement : null;
  const activeId = activeElement?.id;
  const activeLanguage = activeElement?.dataset.language;
  const languageRegion = activeElement?.closest('#footer') ? '#footer' : '#shell';
  const openDetails = [...main.querySelectorAll('details[open][id]')].map((node) => node.id);
  const t = copy[state.locale];
  document.documentElement.lang = state.locale;
  document.title = `Handbalancer’s Studio - ${location.pathname === '/' ? t.heroLines.join(' ') : { '/onboarding': t.goalsTitle, '/register': t.registerTitle.replace('\n', ' '), '/plans': t.plans, '/checkout': t.subscription, '/dashboard': t.account, '/privacy': t.privacy, '/terms': t.terms }[location.pathname] || t.studio}`;
  document.querySelector('meta[name="description"]').content = t.heroBody;
  document.querySelector('.skip-link').textContent =
    state.locale === 'uk' ? 'До основного вмісту' : 'Skip to content';
  shellElement.innerHTML = shell(state);
  main.innerHTML = view(state);
  observeChangeIllustration();
  if (transitioning) lockStepControls(true);
  const pageTitle = main.querySelector('h1');
  if (pageTitle) {
    pageTitle.id = 'page-title';
    pageTitle.tabIndex = -1;
  }
  main.setAttribute('aria-busy', String(state.busy));
  document.querySelector('#footer').innerHTML = footer(state);
  for (const id of openDetails) {
    const node = document.getElementById(id);
    if (node?.tagName === 'DETAILS') node.open = true;
  }
  if (activeId) document.getElementById(activeId)?.focus({ preventScroll: true });
  else if (activeLanguage)
    document
      .querySelector(`${languageRegion} [data-language="${activeLanguage}"]`)
      ?.focus({ preventScroll: true });
  if (focus) focusHeading();
}

// Server routes enforce the same order. These guards make transitions clear in the UI.
function guard() {
  if (state.fatal || !state.session) return;
  const path = location.pathname,
    session = state.session;
  let target = '';
  const incomplete =
    session.user && !session.user.is_demo && (!session.user.first_name || !session.user.last_name);
  if (path === '/dashboard' && !session.user) target = '/login';
  else if (path === '/login' && session.user)
    target = session.onboarding ? '/dashboard' : '/onboarding';
  else if (['/register', '/checkout', '/dashboard'].includes(path) && !session.onboarding)
    target = '/onboarding';
  else if (
    path === '/register' &&
    session.user &&
    !incomplete &&
    new URLSearchParams(location.search).get('edit') !== 'profile'
  )
    target = isActive(state) ? '/dashboard' : session.selected_plan ? '/checkout' : '/plans';
  else if (path === '/register' && !session.user && !session.selected_plan) target = '/plans';
  else if (path === '/checkout' && !session.selected_plan) target = '/plans';
  else if (['/checkout', '/dashboard'].includes(path) && incomplete) target = '/register';
  else if (path === '/checkout' && !session.user) target = '/register';
  else if (path === '/checkout' && isActive(state)) target = '/dashboard';
  if (target) history.replaceState({}, '', target);
}

function navigate(href, { replace = false } = {}) {
  const url = new URL(href, location.origin);
  if (url.origin !== location.origin) return;
  state.menuOpen = false;
  state.error = '';
  if (url.pathname === '/onboarding' && location.pathname !== '/onboarding') state.formStep = 0;
  history[replace ? 'replaceState' : 'pushState']({}, '', url.pathname + url.search + url.hash);
  guard();
  render({ focus: true });
  if (url.hash && location.pathname === url.pathname)
    requestAnimationFrame(() =>
      document.getElementById(url.hash.slice(1))?.scrollIntoView({
        behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
      }),
    );
  else window.scrollTo({ top: 0, behavior: 'instant' });
}

async function refreshSession() {
  state.session = await api('/api/session');
}

async function mutation(action) {
  if (state.busy) return;
  state.error = '';
  state.busy = true;
  render({ preserve: true });
  try {
    await action();
  } catch (error) {
    if (error.status === 402) navigate('/plans');
    else state.error = errorText(error);
  } finally {
    state.busy = false;
    render({ preserve: true });
    if (state.error) {
      main.querySelector('[role="alert"]')?.scrollIntoView({ block: 'nearest' });
      announce(state.error);
    }
  }
}

function invalidStep(index) {
  const d = state.draft,
    t = copy[state.locale];
  if (index === 0 && !d.goals.length) return t.formErrorGoals;
  if (index === 1 && !['beginner', 'intermediate', 'advanced'].includes(d.experience))
    return t.formErrorExperience;
  if (index === 2 && (![30, 45, 60, 90].includes(d.minutes) || d.minutes_plus))
    return t.formErrorMinutes;
  if (index === 3 && (!d.days.length || d.days.length > 3)) return t.formErrorDays;
  return '';
}

// Animate only deliberate step changes, never checkbox changes or error messages.
let transitioning = false;
function lockStepControls(locked) {
  const panel = main.querySelector('.onboarding-slide');
  if (!panel) return;
  panel.dataset.transitioning = String(locked);
  panel.inert = locked;
  // Native disabled controls make the short transition equally clear to keyboard,
  // pointer and browser automation, while retaining the calendar's own limits.
  for (const control of panel.querySelectorAll('input, button, select')) {
    if (locked && !control.disabled) {
      control.dataset.transitionDisabled = 'true';
      control.disabled = true;
    } else if (!locked && control.dataset.transitionDisabled) {
      control.disabled = false;
      delete control.dataset.transitionDisabled;
    }
  }
}
async function changeStep(next) {
  if (transitioning || state.busy) return;
  transitioning = true;
  lockStepControls(true);
  const direction = next > state.formStep ? 1 : -1;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  try {
    const panel = main.querySelector('.onboarding-slide');
    if (panel && !reduced)
      await panel.animate(
        [
          { opacity: 1, transform: 'translateX(0)' },
          { opacity: 0, transform: `translateX(${-24 * direction}px)` },
        ],
        { duration: 160, easing: 'ease-in', fill: 'forwards' },
      ).finished;
    if (location.pathname !== '/onboarding') return;
    state.formStep = next;
    state.error = '';
    render();
    // A shorter next step must remain readable after scrolling a tall mobile form.
    const nextPanel = main.querySelector('.onboarding-slide');
    if (nextPanel && nextPanel.getBoundingClientRect().top < 24) {
      window.scrollTo({
        top: window.scrollY + nextPanel.getBoundingClientRect().top - 24,
        behavior: reduced ? 'instant' : 'smooth',
      });
    }
    if (!reduced)
      await main.querySelector('.onboarding-slide')?.animate(
        [
          { opacity: 0, transform: `translateX(${24 * direction}px)` },
          { opacity: 1, transform: 'translateX(0)' },
        ],
        { duration: 260, easing: 'cubic-bezier(.2,.7,.2,1)' },
      ).finished;
  } catch (error) {
    // Navigation or a new render can cancel an animation. Controls must still unlock.
    if (error.name !== 'AbortError') {
      state.error = copy[state.locale].requestError;
      render();
      announce(state.error);
    }
  } finally {
    transitioning = false;
    lockStepControls(false);
    if (location.pathname === '/onboarding') focusHeading();
  }
}

function updateDraft(input) {
  const d = state.draft,
    { name, value, checked } = input;
  if (name === 'goals')
    d.goals = checked ? [...new Set([...d.goals, value])] : d.goals.filter((id) => id !== value);
  else if (name === 'experience') d.experience = value;
  else if (name === 'days') {
    if (checked && d.days.length >= 3) return;
    d.days = (
      checked
        ? [...new Set([...d.days, Number(value)])]
        : d.days.filter((day) => day !== Number(value))
    ).sort((a, b) => a - b);
  } else if (name === 'minutes') {
    d.minutes = Number(value);
    d.minutes_plus = false;
  }
  d.locale = state.locale;
  saveDraft();
  state.error = '';
}

document.addEventListener('input', (event) => {
  if (event.target.id === 'preview-name') state.previewName = event.target.value;
});

document.addEventListener('change', (event) => {
  if (event.target.closest('#onboarding-form')) {
    updateDraft(event.target);
    render({ preserve: true });
  }
});

document.addEventListener('submit', (event) => {
  if (event.target.id === 'onboarding-form') {
    event.preventDefault();
    if (transitioning) return;
    // Read the visible radio selection too: browser restoration may omit a change event.
    if (state.formStep === 2) {
      const selected = event.target.querySelector('input[name="minutes"]:checked');
      if (selected) updateDraft(selected);
    }
    state.error = invalidStep(state.formStep);
    if (state.error) {
      render({ preserve: true });
      announce(state.error);
      return;
    }
    if (state.formStep < 3) {
      changeStep(state.formStep + 1);
      return;
    }
    for (let i = 0; i < 4; i++) {
      const error = invalidStep(i);
      if (error) {
        state.formStep = i;
        state.error = error;
        render({ focus: true });
        return;
      }
    }
    mutation(async () => {
      state.draft.locale = state.locale;
      const result = await api('/api/onboarding', state.draft);
      state.session.onboarding = result.onboarding;
      saveDraft(false);
      announce(copy[state.locale].saved);
      navigate(state.session.user ? '/dashboard' : '/plans');
    });
  }
  if (
    ['email-register-form', 'verify-form', 'login-form', 'profile-form', 'training-form'].includes(
      event.target.id,
    )
  ) {
    event.preventDefault();
    const form = event.target;
    const payload = Object.fromEntries(new FormData(form));
    const type = form.id;
    if (type === 'email-register-form')
      state.registration = {
        first_name: payload.first_name,
        last_name: payload.last_name,
        email: payload.email,
      };
    mutation(async () => {
      try {
        if (type === 'email-register-form') {
          await api('/api/auth/register', payload);
          state.authStage = 'verify';
        } else if (type === 'verify-form' || type === 'login-form') {
          const result = await api(
            type === 'verify-form' ? '/api/auth/verify' : '/api/auth/login',
            payload,
          );
          await refreshSession();
          state.draft = normaliseDraft(state.session.onboarding);
          state.authStage = 'register';
          state.registration = {};
          state.selectedPlan = state.session.selected_plan || state.selectedPlan;
          saveDraft(false);
          navigate(type === 'login-form' && isActive(state) ? '/dashboard' : result.url);
        } else if (type === 'profile-form') {
          await api('/api/profile', payload, 'PATCH');
          await refreshSession();
          if (location.pathname === '/register')
            navigate(state.session.selected_plan ? '/checkout' : '/plans');
        } else {
          await api('/api/training-sessions', {
            minutes: Number(payload.minutes),
            goal: payload.goal,
          });
          await refreshSession();
        }
      } catch (error) {
        if (type.includes('login') || type.includes('verify') || type.includes('register')) {
          state.error =
            memberCopy[state.locale][
              error.status === 429
                ? 'rateError'
                : error.status === 503
                  ? 'emailUnavailable'
                  : 'authError'
            ];
        } else throw error;
      }
    });
  }
});

document.addEventListener('click', (event) => {
  const link = event.target.closest('a[data-route]');
  if (
    link &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey &&
    event.button === 0
  ) {
    event.preventDefault();
    navigate(link.href);
    return;
  }
  // Clicking the card surface uses the same accessible button action.
  const button =
    event.target.closest('button') ||
    event.target.closest('.plan-card')?.querySelector('[data-plan]');
  if (!button || button.disabled) return;
  if (button.id === 'menu-toggle') {
    state.menuOpen = !state.menuOpen;
    render();
    if (state.menuOpen) document.querySelector('#main-navigation a')?.focus();
    else document.querySelector('#menu-toggle')?.focus();
  } else if (button.dataset.language) {
    const languageRegion = button.closest('#footer') ? '#footer' : '#shell';
    const locale = button.dataset.language;
    if (locale === state.locale) return;
    state.locale = locale;
    state.draft.locale = locale;
    write(STORAGE.locale, locale);
    saveDraft();
    state.error = '';
    render();
    document
      .querySelector(`${languageRegion} [data-language="${locale}"]`)
      ?.focus({ preventScroll: true });
    // A completed document can be updated without sending an unfinished local draft.
    const completed = state.session?.onboarding;
    if (
      completed &&
      [30, 45, 60, 90].includes(completed.minutes) &&
      completed.days.length <= 3 &&
      !state.busy
    )
      mutation(async () => {
        const result = await api('/api/onboarding', {
          ...normaliseDraft(state.session.onboarding),
          locale,
        });
        state.session.onboarding = result.onboarding;
      });
  } else if (button.hasAttribute('data-form-back')) {
    changeStep(Math.max(0, state.formStep - 1));
  } else if (button.dataset.direction) {
    state.draft.goals = [button.dataset.direction];
    saveDraft();
    navigate('/onboarding');
  } else if (button.dataset.plan) {
    state.selectedPlan = button.dataset.plan;
    write(STORAGE.plan, state.selectedPlan);
    // Preserve the cards in the DOM so CSS can animate only the chosen one.
    document.querySelectorAll('.plan-card').forEach((card) => {
      const control = card.querySelector('[data-plan]');
      const selected = control.dataset.plan === state.selectedPlan;
      card.classList.toggle('selected', selected);
      control.setAttribute('aria-pressed', String(selected));
    });
    const continuation = document.querySelector('[data-plan-continue]');
    continuation.disabled = false;
    continuation.textContent = `${copy[state.locale].continuePlan} ${button.dataset.plan === 'pro_plus' ? 'Pro+' : button.dataset.plan[0].toUpperCase() + button.dataset.plan.slice(1)} →`;
    announce(
      `${copy[state.locale].chosenPlan}: ${button.dataset.plan === 'pro_plus' ? 'Pro+' : button.dataset.plan}`,
    );
  } else if (button.hasAttribute('data-auth-restart')) {
    state.authStage = 'register';
    render();
  } else if (button.hasAttribute('data-billing-portal')) {
    mutation(async () => {
      const result = await api('/api/billing-portal', {});
      const url = new URL(result.url);
      if (url.protocol !== 'https:' || url.hostname !== 'billing.stripe.com')
        throw new RequestError(502);
      location.assign(url.href);
    });
  } else if (button.hasAttribute('data-plan-continue') && state.selectedPlan) {
    mutation(async () => {
      await api('/api/plan', { plan_id: state.selectedPlan });
      state.session.selected_plan = state.selectedPlan;
      navigate(
        !state.session.onboarding
          ? '/onboarding'
          : !state.session.user
            ? '/register'
            : `/checkout?plan=${state.selectedPlan}`,
      );
    });
  } else if (button.hasAttribute('data-demo-pay'))
    mutation(async () => {
      await api('/api/checkout', { plan_id: state.selectedPlan });
      await api('/api/preview/pay', { plan_id: state.selectedPlan });
      await refreshSession();
      navigate('/dashboard');
    });
  else if (button.hasAttribute('data-checkout'))
    mutation(async () => {
      const result = await api('/api/checkout', { plan_id: state.selectedPlan });
      const url = new URL(result.url, location.origin);
      if (url.protocol !== 'https:' || url.hostname !== 'checkout.stripe.com')
        throw new RequestError(502);
      location.assign(url.href);
    });
  else if (button.hasAttribute('data-refresh'))
    mutation(async () => {
      await refreshSession();
      guard();
      render({ focus: true });
    });
  else if (button.hasAttribute('data-logout'))
    mutation(async () => {
      await api('/api/logout', {});
      remove(STORAGE.draft);
      remove(STORAGE.plan);
      state.draft = blankDraft();
      state.draft.locale = state.locale;
      state.selectedPlan = 'plus';
      state.previewName = '';
      state.authStage = 'register';
      state.registration = {};
      await refreshSession();
      navigate('/');
    });
  else if (button.hasAttribute('data-retry')) boot();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && state.menuOpen) {
    state.menuOpen = false;
    render();
    document.querySelector('#menu-toggle')?.focus();
  }
});
window.addEventListener('popstate', () => {
  state.error = '';
  state.menuOpen = false;
  guard();
  render({ focus: true });
});

async function refreshCheckoutStatus() {
  // Stripe may redirect before its signed webhook has reached our database.
  for (let attempt = 0; attempt < 10 && !isActive(state); attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    if (location.pathname !== '/dashboard') return;
    try {
      await refreshSession();
      render({ preserve: true });
    } catch {
      return;
    }
  }
}

async function boot() {
  state.fatal = false;
  state.error = '';
  try {
    const [session, plans] = await Promise.all([api('/api/session'), api('/api/plans')]);
    state.session = session;
    if (session.selected_plan) state.selectedPlan = session.selected_plan;
    state.authStage = session.verification_pending ? 'verify' : 'register';
    state.plans = plans.plans.filter(
      (plan) =>
        planIds.includes(plan.id) &&
        Number.isInteger(plan.price_cents) &&
        plan.price_cents > 0 &&
        plan.currency === 'EUR',
    );
    const saved = read(STORAGE.draft);
    const sameOwner = saved?.owner === (session.user?.id || null);
    state.draft = normaliseDraft(
      saved?.dirty && sameOwner
        ? saved.document
        : session.onboarding || (sameOwner && saved?.document),
    );
    if (!storedLocale && session.onboarding?.locale) state.locale = session.onboarding.locale;
    state.draft.locale = state.locale;
    const requestedPlan = new URLSearchParams(location.search).get('plan');
    if (planIds.includes(requestedPlan)) {
      state.selectedPlan = requestedPlan;
      write(STORAGE.plan, requestedPlan);
    }
    guard();
    render();
    if (
      location.pathname === '/dashboard' &&
      new URLSearchParams(location.search).get('checkout') === 'success'
    )
      refreshCheckoutStatus();
    if (location.hash)
      requestAnimationFrame(() =>
        document.getElementById(location.hash.slice(1))?.scrollIntoView(),
      );
  } catch {
    state.fatal = true;
    render();
  }
}

boot();

// Reconcile expiring access and weekly totals while the dashboard stays open.
setInterval(async () => {
  if (
    location.pathname !== '/dashboard' ||
    document.hidden ||
    state.busy ||
    main.querySelector('details[open]')
  )
    return;
  try {
    await refreshSession();
    render({ preserve: true });
  } catch {
    /* Keep the last known view on a transient network error. */
  }
}, 60000);
