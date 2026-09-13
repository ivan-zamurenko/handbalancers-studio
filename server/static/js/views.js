import { icon } from './icons.js';
import { copy, goalIds, planIds, planNames } from './copy.js';

// Every dynamic value, including account names and saved form data, is escaped.
export const escapeHtml = (value = '') =>
  String(value).replace(
    /[&<>"']/g,
    (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char],
  );
const e = escapeHtml;
const heading = (value) => value.split('\n').map(e).join('<br>');
const arrow = '<span aria-hidden="true">↗</span>';
const routeLink = (href, label, cls = 'button') =>
  `<a class="${cls}" href="${href}" data-route>${label}</a>`;
const badge = (label) => `<span class="chip">${e(label)}</span>`;
const errorMessage = (state) =>
  state.error ? `<div class="message error" role="alert">${e(state.error)}</div>` : '';
const isActive = (state) =>
  Boolean(
    state.session?.subscription &&
    ['active', 'trialing'].includes(state.session.subscription.status),
  );
const price = (state, id) => {
  const plan = state.plans.find((item) => item.id === id);
  return plan
    ? new Intl.NumberFormat(state.locale === 'uk' ? 'uk-UA' : 'en-IE', {
        style: 'currency',
        currency: plan.currency,
        currencyDisplay: 'narrowSymbol',
      }).format(plan.price_cents / 100)
    : '-';
};

export function shell(state) {
  const t = copy[state.locale];
  return `${state.session?.local_preview && !['/', '/plans'].includes(location.pathname) ? `<aside class="local-bar"><span class="status-dot" aria-hidden="true"></span><span>${e(t.local)} <span class="local-detail">· ${e(t.localNote)}</span></span></aside>` : ''}
    <header class="site-header"><div class="header-inner">
      <a class="brand" href="/" data-route aria-label="Handbalancer’s Studio - ${e(t.home)}"><span class="brand-mark" aria-hidden="true">h<span>.</span></span><span>Handbalancer’s<br>Studio</span></a>
      <button class="menu-button" type="button" id="menu-toggle" aria-expanded="${state.menuOpen}" aria-controls="main-navigation" aria-label="${e(state.menuOpen ? t.closeMenu : t.openMenu)}"><span></span><span></span></button>
      <nav id="main-navigation" class="navigation ${state.menuOpen ? 'is-open' : ''}" aria-label="${e(t.navigation)}">
        <a href="/#directions" data-route>${e(t.directions)}</a><a href="/#method" data-route>${e(t.method)}</a><a href="/#plans" data-route>${e(t.plans)}</a>${routeLink(state.session?.user ? '/dashboard' : '/register', e(t.login), 'mobile-account')}
      </nav>
      <div class="header-actions"><div class="language-switch" role="group" aria-label="Language / Мова"><button type="button" data-language="uk" lang="uk" aria-label="Українська" aria-pressed="${state.locale === 'uk'}">UA</button><button type="button" data-language="en" lang="en" aria-label="English" aria-pressed="${state.locale === 'en'}">EN</button></div>${routeLink(state.session?.user ? '/dashboard' : '/register', e(t.login), 'header-account')}</div>
    </div></header>`;
}

export function footer(state) {
  const t = copy[state.locale];
  return `<div class="footer-inner"><div><a class="footer-brand" href="/" data-route>Handbalancer’s Studio<span aria-hidden="true">↗</span></a><p>${e(t.footer)}</p></div><nav aria-label="${e(t.terms)}">${routeLink('/privacy', e(t.privacy), 'text-link')}${routeLink('/terms', e(t.terms), 'text-link')}</nav><span class="footer-year">© ${new Date().getFullYear()}</span></div>`;
}

function stepper(state, index) {
  const t = copy[state.locale];
  return `<ol class="stepper" aria-label="${e(t.stages)}">${t.steps.map((label, i) => `<li ${i === index ? 'aria-current="step"' : ''} class="${i < index ? 'complete' : ''}"><span aria-hidden="true">${i < index ? '✓' : `0${i + 1}`}</span><span>${e(label)}</span></li>`).join('')}</ol>`;
}

function planCards(state) {
  const t = copy[state.locale];
  return `<div class="plan-grid">${planIds.map((id, i) => `<article class="plan-card ${state.selectedPlan === id ? 'selected' : ''}"><p class="plan-tag">${i === 1 ? `<span class="recommendation-badge">${e(t.recommended)}</span>` : '&nbsp;'}</p><h3>${e(planNames[id])}</h3><p class="plan-description">${e(t.planDescriptions[i])}</p><div class="price">${e(price(state, id))}</div><p class="period">${e(t.month)}</p><button class="button plan-select" type="button" data-plan="${id}" aria-pressed="${state.selectedPlan === id}" ${state.busy || !state.plans.some((p) => p.id === id) ? 'disabled' : ''}>${e(t.choose)} ${e(planNames[id])}</button><div class="plan-features"><p>${e(t.includes[i])}</p><ul>${t.features[i].map((f) => `<li>${e(f)}</li>`).join('')}</ul></div></article>`).join('')}</div><div class="plan-action"><button type="button" class="button primary" data-plan-continue ${!state.selectedPlan || state.busy ? 'disabled' : ''}>${state.selectedPlan ? `${e(t.continuePlan)} ${e(planNames[state.selectedPlan])} →` : e(t.selectPlanFirst)}</button></div>`;
}

// The upward line is a visual direction, not measured health data or a forecast.
function transformation(state) {
  const t = copy[state.locale].needs;
  return `<section id="philosophy" class="section needs-section" aria-labelledby="needs-heading">
    <h2 id="needs-heading" class="display change-heading">${e(t.titleParts[0])} <span class="change-heading-before">${e(t.titleParts[1])}</span> ${e(t.titleParts[2])} <span class="change-heading-after">${e(t.titleParts[3])}</span></h2>
    <ol class="change-grid">
      <li class="change-card change-before"><p class="change-stage">${e(t.stages[0])}</p><h3>${e(t.titles[0])}</h3><ul class="change-list">${t.problems.map((item) => `<li><span aria-hidden="true">−</span>${e(item)}</li>`).join('')}</ul><span class="change-connector" aria-hidden="true">→</span></li>
      <li class="change-card change-support"><p class="change-stage">${e(t.stages[1])}</p><h3>${e(t.titles[1])}</h3><ul class="change-actions">${t.support.map(([title, body]) => `<li><span class="change-check" aria-hidden="true">✓</span><div><h4>${e(title)}</h4><p>${e(body)}</p></div></li>`).join('')}</ul><span class="change-connector" aria-hidden="true">→</span></li>
      <li class="change-card change-after"><p class="change-stage">${e(t.stages[2])}</p><h3>${e(t.titles[2])}</h3><div class="change-trend"><svg viewBox="0 0 300 84" fill="none" aria-hidden="true"><path class="change-trend-base" d="M8 73H292"/><path class="change-rise" pathLength="1" d="M9 68C47 70 51 49 83 52S127 64 156 41S207 48 238 26L284 10"/><path d="m270 7 15 3-7 14"/></svg></div><ul class="change-list">${t.outcomes.map((item) => `<li><span aria-hidden="true">✓</span>${e(item)}</li>`).join('')}</ul></li>
    </ol></section>`;
}

function landing(state) {
  const t = copy[state.locale];
  return `<section class="hero section-wide"><div class="hero-copy"><p class="eyebrow"><span class="status-dot" aria-hidden="true"></span>${e(t.heroEyebrow)}</p><h1>${t.heroLines.map((line) => `<span>${e(line)}</span>`).join('')}</h1><p class="intro">${e(t.heroBody)}</p><div class="hero-actions">${routeLink('/onboarding', `${e(t.start)} ${arrow}`, 'button primary')}${routeLink('/#plans', `${e(t.seePlans)} <span aria-hidden="true">→</span>`, 'text-link')}</div></div><figure class="hero-figure"><img src="/static/images/hero.webp" width="1536" height="1024" fetchpriority="high" alt="${e(t.heroAlt)}"></figure></section>
    ${transformation(state)}
    <section id="directions" class="section directions"><div class="section-heading"><div><p class="eyebrow">${e(t.directionsEyebrow)}</p><h2 class="display">${heading(t.directionsTitle)}</h2></div><p class="intro">${e(t.directionsBody)}</p></div><div class="direction-grid">${goalIds.map((id, i) => `<article class="direction-card"><div class="direction-top"><span class="direction-symbol symbol-${id}" aria-hidden="true">${icon(id)}</span></div><h3>${e(t.goalTitles[id])}</h3><p>${e(t.goalLong[id])}</p><button type="button" data-direction="${id}" class="direction-link" aria-label="${e(t.chooseDirection)}: ${e(t.goalTitles[id])}">${e(t.chooseDirection)} ${arrow}</button></article>`).join('')}</div></section>
    <section id="method" class="section method-section"><figure class="practice-figure"><img src="/static/images/practice.webp" width="1536" height="1024" loading="lazy" alt="${e(t.practiceAlt)}"></figure><div class="method-copy"><p class="eyebrow">${e(t.methodEyebrow)}</p><h2 class="display">${heading(t.methodTitle)}</h2><p class="intro">${e(t.methodBody)}</p><ol class="method-steps">${t.methodSteps.map((item, i) => `<li><span aria-hidden="true">0${i + 1}</span><div><h3>${e(item[0])}</h3><p>${e(item[1])}</p></div></li>`).join('')}</ol></div></section>
    <section id="plans" class="section pricing-section"><div class="section-heading center"><p class="eyebrow">${e(t.supportEyebrow)}</p><h2 class="display">${heading(t.plansTitle)}</h2><p class="intro">${e(t.plansIntro)}</p></div>${planCards(state)}</section>
    <section id="equipment" class="section equipment-section"><div class="equipment-copy"><p class="eyebrow">${e(t.equipmentEyebrow)}</p><h2 class="display">${heading(t.equipmentTitle)}</h2><p class="intro">${e(t.equipmentBody)}</p><div class="chips">${['mat', 'parallettes', 'blocks'].map((id) => badge(t.equipmentNames[id])).join('')}</div></div><figure><img src="/static/images/equipment.webp" width="1536" height="1024" loading="lazy" alt="${e(t.equipmentAlt)}"></figure></section>
    <section id="faq" class="section faq-section"><div><p class="eyebrow">${e(t.faqEyebrow)}</p><h2 class="display">${e(t.faqTitle)}</h2></div><div class="faq-list">${t.faq.map((item, i) => `<details id="faq-${i}"><summary>${e(item[0])}<span aria-hidden="true">＋</span></summary><p>${e(item[1])}</p></details>`).join('')}</div></section>
    <section class="section final-cta center"><span class="cta-mark" aria-hidden="true">h<span>.</span></span><h2 class="display">${heading(t.finalTitle)}</h2><p class="intro">${e(t.finalBody)}</p>${routeLink('/onboarding', `${e(t.start)} ${arrow}`, 'button primary')}</section>`;
}

function selectionSummary(state, document = state.draft) {
  const t = copy[state.locale];
  return `<div class="chips">${document.goals.map((id) => badge(t.goalTitles[id])).join('')}</div>`;
}

function onboarding(state) {
  const t = copy[state.locale],
    d = state.draft,
    s = state.formStep;
  const titles = [t.goalsTitle, t.experienceTitle, t.timeTitle, t.rhythmTitle];
  const intros = [t.goalsIntro, t.experienceIntro, t.timeIntro, t.rhythmIntro];
  let body = '';
  if (s === 0)
    body = `<fieldset><legend class="sr-only">${e(t.goalsTitle)}</legend><div class="goal-options">${goalIds.map((id) => `<label class="choice-card ${d.goals.includes(id) ? 'selected' : ''}"><input type="checkbox" name="goals" value="${id}" id="goal-${id}" ${d.goals.includes(id) ? 'checked' : ''}><span class="choice-symbol">${icon(id)}</span><span><strong>${e(t.goalTitles[id])}</strong><small>${e(t.goalDescriptions[id])}</small></span><span class="choice-check" aria-hidden="true"></span></label>`).join('')}</div></fieldset>`;
  if (s === 1)
    body = `<fieldset><legend class="sr-only">${e(t.experienceTitle)}</legend><div class="experience-options">${Object.entries(
      t.experience,
    )
      .map(
        ([id, item], i) =>
          `<label class="choice-card ${d.experience === id ? 'selected' : ''}"><input type="radio" name="experience" value="${id}" id="experience-${id}" ${d.experience === id ? 'checked' : ''}><span class="experience-number" aria-hidden="true">${i + 1}</span><span><strong>${e(item[0])}</strong><small>${e(item[1])}</small></span><span class="choice-check" aria-hidden="true"></span></label>`,
      )
      .join('')}</div></fieldset>`;
  if (s === 2)
    body = `<fieldset class="form-group"><legend class="sr-only">${e(t.minutesLabel)}</legend><div class="duration-options">${[
      30,
      45,
      60,
      '60-plus',
    ]
      .map((n) => {
        const selected =
          n === '60-plus' ? d.minutes === 60 && d.minutes_plus : d.minutes === n && !d.minutes_plus;
        return `<label class="duration-choice ${selected ? 'selected' : ''}"><input type="radio" name="minutes" value="${n}" id="minutes-${n}" ${selected ? 'checked' : ''}><span class="duration-icon">${icon('clock')}</span><strong>${n === '60-plus' ? '60+' : n}</strong><small>${e(t.minutes)}</small></label>`;
      })
      .join('')}</div></fieldset>`;
  if (s === 3)
    body = `<fieldset class="form-group"><legend class="sr-only">${e(t.daysLabel)}</legend><div class="day-options">${t.weekdays.map((day, i) => `<label class="day-choice ${d.days.includes(i) ? 'selected' : ''} ${!d.days.includes(i) && d.days.length >= 3 ? 'unavailable' : ''}"><input type="checkbox" name="days" value="${i}" id="day-${i}" aria-describedby="days-limit" ${d.days.includes(i) ? 'checked' : ''} ${!d.days.includes(i) && d.days.length >= 3 ? 'disabled' : ''}><span class="calendar-day" aria-hidden="true">${['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}</span><span class="calendar-name">${e(day)}</span></label>`).join('')}</div><p id="days-limit" class="field-hint">${e(t.daysHint)} · ${d.days.length}/3</p></fieldset><aside class="form-review"><p class="eyebrow">${e(t.reviewTitle)}</p>${selectionSummary(state)}<p>${e(t.experience[d.experience]?.[0] || '')} · ${d.minutes}${d.minutes_plus ? '+' : ''} ${e(t.minutes)}${d.days.length ? ` · ${d.days.map((i) => e(t.weekdaysShort[i])).join(', ')}` : ''}</p></aside>`;
  return `<section class="section flow-section">${stepper(state, 0)}<div class="form-progress"><span>${e(t.formProgress)} 0${s + 1} ${e(t.of)} 04</span><span>${e(t.formSections[s])}</span><div class="progress-track"><span class="progress-${s + 1}"></span></div></div><div class="onboarding-slide"><h1 class="flow-title">${e(titles[s])}</h1><p class="intro">${e(intros[s])}</p><form id="onboarding-form" novalidate>${errorMessage(state)}${body}<p class="form-value">${e(t.formValues[s])}</p><div class="form-actions">${s > 0 ? `<button type="button" class="text-link" data-form-back>← ${e(t.back)}</button>` : `<span class="field-hint">${e(t.selectedGoals)}: ${d.goals.length}</span>`}<button type="submit" class="button primary" ${state.busy ? 'disabled' : ''}>${e(state.busy ? t.working : s === 3 ? (state.session?.user ? t.save : t.saveAndContinue) : t.next)} ${arrow}</button></div><p class="draft-note">${e(t.draftNote)}</p></form></div></section>`;
}

function register(state) {
  const t = copy[state.locale];
  const authError = new URLSearchParams(location.search).get('auth_error');
  return `<section class="section flow-section register-section">${stepper(state, 1)}<div class="center"><p class="eyebrow">Handbalancer’s Studio</p><h1 class="flow-title">${heading(t.registerTitle)}</h1><p class="intro">${e(t.registerIntro)}</p>${selectionSummary(state, state.session.onboarding)}</div>${errorMessage(state)}${authError ? `<p class="message error" role="alert">${e(authError === 'unavailable' ? t.authUnavailable : t.authError)}</p>` : ''}<div class="auth-options">${['google', 'apple'].map((provider) => (state.session.providers[provider] ? `<a class="button auth-button" href="/auth/${provider}/login"><span class="provider-mark" aria-hidden="true">${provider === 'google' ? 'G' : '●'}</span>${e(t[provider])}</a>` : `<button class="button auth-button" type="button" disabled><span class="provider-mark" aria-hidden="true">${provider === 'google' ? 'G' : '●'}</span><span>${e(t[provider])}<small>${e(t.providerUnavailable)}</small></span></button>`)).join('')}<p class="fine-note center">${e(t.providerNote)}</p></div>${state.session.local_preview ? `<div class="demo-panel"><span class="demo-label">${e(t.previewTitle)}</span><form id="register-form"><div class="field"><label for="preview-name">${e(t.previewName)}</label><input id="preview-name" name="name" autocomplete="given-name" minlength="1" maxlength="80" placeholder="${e(t.previewPlaceholder)}" required value="${e(state.previewName || '')}"></div><button class="button primary full-width" type="submit" ${state.busy ? 'disabled' : ''}>${e(state.busy ? t.working : t.previewRegister)} ${arrow}</button></form><p class="fine-note">${e(t.previewRegisterNote)}</p></div>` : ''}<p class="legal-links">${e(t.legalBefore)} ${routeLink('/terms', e(t.terms), 'text-link')} ${e(t.legalAnd)} ${routeLink('/privacy', e(t.privacy), 'text-link')}.</p><div class="center">${routeLink('/onboarding', `← ${e(t.edit)}`, 'text-link')}</div></section>`;
}

function plans(state) {
  const t = copy[state.locale];
  return `<section class="section plans-page">${state.session.user && state.session.onboarding ? stepper(state, 2) : ''}<div class="section-heading center"><p class="eyebrow">${e(t.supportEyebrow)}</p><h1 class="display">${heading(t.plansTitle)}</h1><p class="intro">${e(t.plansIntro)}</p>${state.session.onboarding ? selectionSummary(state, state.session.onboarding) : ''}</div>${errorMessage(state)}${planCards(state)}</section>`;
}

function checkout(state) {
  const t = copy[state.locale],
    id = state.selectedPlan,
    i = planIds.indexOf(id);
  const params = new URLSearchParams(location.search);
  return `<section class="section flow-section checkout-section">${stepper(state, 3)}<div class="center"><p class="eyebrow">Handbalancer’s Studio</p><h1 class="flow-title">${heading(t.checkoutTitle)}</h1><p class="intro">${e(t.checkoutIntro)}</p></div>${errorMessage(state)}${params.has('canceled') ? `<p class="message">${e(t.canceledPayment)}</p>` : ''}${params.has('success') ? `<p class="message">${e(t.pendingPayment)} <button type="button" class="text-link" data-refresh>${e(t.refreshStatus)}</button></p>` : ''}<article class="checkout-card"><div class="checkout-plan"><div><p class="eyebrow">${e(t.subscription)}</p><h2>${e(planNames[id])}</h2></div>${badge(state.session.local_preview ? t.local : t.monthly)}</div><p class="muted">${e(t.planDescriptions[i])}</p><div class="plan-features"><p>${e(t.includes[i])}</p><ul>${t.features[i].map((item) => `<li>${e(item)}</li>`).join('')}</ul></div><dl class="checkout-total"><div><dt>${e(t.period)}</dt><dd>${e(t.monthly)}</dd></div><div><dt>${e(t.monthlyTotal)}</dt><dd class="checkout-price">${e(price(state, id))}</dd></div></dl>${state.session.payments_enabled && !state.session.user.is_demo ? `<button type="button" class="button primary full-width" data-checkout ${state.busy ? 'disabled' : ''}>${e(state.busy ? t.working : t.pay)} ${arrow}</button>` : `<div class="message"><strong>${e(t.paymentUnavailable)}</strong><p>${e(t.paymentUnavailableBody)}</p></div>`}${state.session.local_preview && state.session.user.is_demo ? `<div class="demo-payment"><span class="demo-label">${e(t.local)}</span><p>${e(t.demoPayNote)}</p><button type="button" class="button primary full-width" data-demo-pay ${state.busy ? 'disabled' : ''}>${e(state.busy ? t.working : t.demoPay)} ${arrow}</button></div>` : ''}</article><div class="center">${routeLink('/plans', `← ${e(t.changePlan)}`, 'text-link')}</div></section>`;
}

function dashboard(state) {
  const t = copy[state.locale],
    d = state.session.onboarding,
    sub = state.session.subscription;
  return `<section class="section dashboard-section"><div class="dashboard-heading"><div><p class="eyebrow">${e(t.dashboardEyebrow)}</p><p class="greeting">${e(t.greeting)}, ${e(state.session.user.name)}.</p><h1 class="display">${e(t.dashboardTitle)}</h1><p class="intro">${e(t.dashboardIntro)}</p></div><div class="member-plan"><span class="status-dot" aria-hidden="true"></span><span>${e(sub.is_demo ? t.demoBadge : t.activeBadge)}</span><strong>${e(planNames[sub.plan_id] || sub.plan_id)}</strong></div></div>${errorMessage(state)}<div class="dashboard-grid"><article class="dashboard-card goals-card"><p class="eyebrow">01 / ${e(t.goalsSummary)}</p><h2>${e(t.experience[d.experience][0])}</h2>${selectionSummary(state, d)}${routeLink('/onboarding', `${e(t.edit)} ${arrow}`, 'text-link')}</article><article class="dashboard-card"><p class="eyebrow">02 / ${e(t.scheduleSummary)}</p><h2>${d.minutes}${d.minutes_plus ? '+' : ''} <span>${e(t.minutes)}</span></h2><div class="dashboard-days">${t.weekdays.map((day, i) => `<span class="${d.days.includes(i) ? 'scheduled' : ''}" aria-label="${e(day)}${d.days.includes(i) ? ` - ${e(t.daysLabel)}` : ''}">${e(t.weekdaysShort[i])}</span>`).join('')}</div><p class="muted">${e(d.timezone)}</p></article><article class="dashboard-card"><p class="eyebrow">03 / ${e(t.profile)}</p><h2>${e(state.session.user.name)}</h2><p class="muted">${e(t.saved)}</p></article></div><article class="assessment-card"><div class="assessment-mark" aria-hidden="true">↗</div><div><p class="eyebrow">${e(t.nextStep)}</p><h2>${e(t.assessmentTitle)}</h2><p>${e(t.assessmentBody)}</p></div>${badge(t.pending)}</article><p class="empty-history">${e(t.dashboardEmpty)}</p><div class="dashboard-bottom"><span>${e(t.profile)}: ${e(state.session.user.name)}</span><button class="text-link" type="button" data-logout ${state.busy ? 'disabled' : ''}>${e(t.logout)} <span aria-hidden="true">↗</span></button></div></section>`;
}

function legal(state, path) {
  const t = copy[state.locale],
    privacy = path === '/privacy';
  return `<article class="section legal-page"><p class="eyebrow"><span class="status-dot amber" aria-hidden="true"></span>${e(t.draftLabel)}</p><h1 class="display">${e(privacy ? t.legalTitlePrivacy : t.legalTitleTerms)}</h1><p class="message">${e(t.legalDraft)}</p>${(privacy ? t.privacySections : t.termsSections).map((item, i) => `<section><h2><span>0${i + 1}</span>${e(item[0])}</h2><p>${e(item[1])}</p></section>`).join('')}${routeLink('/', `← ${e(t.backHome)}`, 'text-link')}</article>`;
}

export function view(state) {
  if (state.fatal)
    return `<section class="section flow-section"><h1 class="flow-title">${e(copy[state.locale].networkError)}</h1><button type="button" data-retry class="button primary">${e(copy[state.locale].retry)}</button></section>`;
  const path = location.pathname.replace(/\/$/, '') || '/';
  const renderers = {
    '/': landing,
    '/onboarding': onboarding,
    '/register': register,
    '/plans': plans,
    '/checkout': checkout,
    '/dashboard': dashboard,
  };
  if (path === '/privacy' || path === '/terms') return legal(state, path);
  return renderers[path]
    ? renderers[path](state)
    : `<section class="section"><h1>${e(copy[state.locale].unknownPage)}</h1>${routeLink('/', e(copy[state.locale].backHome))}</section>`;
}

export { isActive };
