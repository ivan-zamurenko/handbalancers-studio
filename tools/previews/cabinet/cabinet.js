// Cabinet mock: shared shell, theme switch and synthetic charts. No network, no real data.
const icons = {
  home: '<path d="M4 11 12 4l8 7v9h-5v-6H9v6H4z"/>',
  plan: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 9h6M9 13h6M9 17h4"/>',
  library: '<path d="M4 12h3M17 12h3M7 8v8M17 8v8M7 12h10"/>',
  history: '<path d="M4 12a8 8 0 1 0 3-6.2"/><path d="M4 4v4h4M12 8v4l3 2"/>',
  chart: '<path d="M4 4v16h16"/><path d="m7 15 4-4 3 3 5-6"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
};
const svg = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name]}</svg>`;
const page = document.body.dataset.page;
const nav = [['home', 'Сьогодні', '#'], ['plan', 'Моя програма', '#'], ['library', 'Бібліотека', '#'],
  ['history', 'Історія', '#'], ['chart', 'Прогрес', './progress.html']];
const tabs = [['home', 'Сьогодні', '#'], ['plan', 'Програма', '#'], ['history', 'Історія', '#'],
  ['chart', 'Прогрес', './progress.html'], ['user', 'Профіль', './profile.html']];
const current = href => (href.includes(page) ? ' aria-current="page"' : '');

document.querySelector('[data-side]').innerHTML = `
  <a class="cab-brand" href="/"><span class="wordmark">h<span>.</span></span><small>Handbalancer’s<br>Studio</small></a>
  <nav class="cab-nav" aria-label="Кабінет">${nav.map(([i, t, h]) => `<a href="${h}"${current(h)}>${svg(i)}${t}</a>`).join('')}</nav>
  <a class="cab-user" href="./profile.html"${current('./profile.html')}><span class="avatar">ІЗ</span><span>Іван З.<small>Pro · профіль</small></span></a>`;
document.querySelector('[data-tabs]').innerHTML =
  tabs.map(([i, t, h]) => `<a href="${h}"${current(h)}>${svg(i)}${t}</a>`).join('');

const root = document.documentElement;
const themeButton = document.querySelector('[data-theme-button]');
const syncTheme = () => { themeButton.textContent = root.dataset.theme === 'dark' ? 'Світла тема' : 'Темна тема'; };
themeButton.addEventListener('click', () => { root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; syncTheme(); });
const params = new URLSearchParams(location.search);
if (params.get('theme') === 'light' || params.get('theme') === 'dark') root.dataset.theme = params.get('theme');
syncTheme();

// Deterministic pseudo-random so screenshots are stable.
let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

const heat = document.querySelector('[data-heat]');
if (heat) {
  const today = new Date('2026-11-16T12:00:00');
  const start = new Date(today);
  start.setDate(start.getDate() - start.getDay() - 52 * 7); // Sunday, 53 columns
  const months = ['Січ', 'Лют', 'Бер', 'Кві', 'Тра', 'Чер', 'Лип', 'Сер', 'Вер', 'Жов', 'Лис', 'Гру'];
  const cells = [];
  let lastMonth = -1;
  let active = 0;
  for (let w = 0; w < 53; w++) {
    const day = new Date(start); day.setDate(start.getDate() + w * 7);
    if (day.getMonth() !== lastMonth && w < 51) {
      cells.push(`<span class="m" style="grid-column:${w + 2}">${months[day.getMonth()]}</span>`);
      lastMonth = day.getMonth();
    }
    for (let d = 0; d < 7; d++) {
      const date = new Date(start); date.setDate(start.getDate() + w * 7 + d);
      const ramp = w / 52;
      const planned = [1, 3, 5].includes(d) ? 0.75 : 0.12;
      const practiced = rand() < planned * (0.45 + ramp * 0.6);
      const level = practiced ? Math.min(4, 1 + Math.floor(rand() * 3 + ramp * 1.4)) : 0;
      if (level) active++;
      const future = date > today ? ' future' : '';
      const minutes = [0, 20, 35, 50, 75][level];
      const label = `${date.toLocaleDateString('uk-UA', {day: 'numeric', month: 'long'})}: ${level ? `${minutes} хв` : 'без занять'}`;
      cells.push(`<span class="c${future}" data-l="${level}" style="grid-column:${w + 2};grid-row:${d + 2}" title="${label}"></span>`);
    }
  }
  ['Нд', '', 'Вт', '', 'Чт', '', 'Сб'].forEach((t, d) => cells.push(`<span class="d" style="grid-row:${d + 2}">${t}</span>`));
  heat.innerHTML = cells.join('');
  document.querySelector('[data-heat-count]').textContent = `${active} днів із заняттями за рік`;
  heat.closest('.heat-scroll').scrollLeft = 10_000;
}

function lineChart(el, values, unit) {
  const w = Math.max(280, Math.round(el.getBoundingClientRect().width)), h = 170, pad = {l: 34, r: 12, t: 12, b: 24};
  const max = Math.ceil(Math.max(...values) / 10) * 10 + 10;
  const x = i => pad.l + (i * (w - pad.l - pad.r)) / (values.length - 1);
  const y = v => h - pad.b - (v / max) * (h - pad.t - pad.b);
  const pts = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
  const grid = [0, max / 2, max].map(v => `<line class="grid-line" x1="${pad.l}" x2="${w - pad.r}" y1="${y(v)}" y2="${y(v)}"/><text x="0" y="${y(v) + 4}">${v}${unit}</text>`).join('');
  const labels = values.map((_, i) => (i % (w < 420 ? 4 : 3) === 0 ? `<text x="${x(i) - 8}" y="${h - 4}">т${i + 1}</text>` : '')).join('');
  el.setAttribute('viewBox', `0 0 ${w} ${h}`);
  el.innerHTML = `${grid}<polygon class="area" points="${pad.l},${h - pad.b} ${pts.join(' ')} ${w - pad.r},${h - pad.b}"/>
    <polyline class="line" points="${pts.join(' ')}"/>${values.map((v, i) => `<circle class="pt" r="3.5" cx="${x(i)}" cy="${y(v)}"/>`).join('')}${labels}`;
}
const hold = document.querySelector('[data-hold]');
if (hold) lineChart(hold, [12, 14, 13, 18, 21, 20, 24, 27, 26, 31, 34, 38], 'с');

for (const spark of document.querySelectorAll('[data-spark]')) {
  const values = spark.dataset.spark.split(',').map(Number);
  const max = Math.max(...values), min = Math.min(...values);
  const pts = values.map((v, i) => `${(i * 92) / (values.length - 1) + 2},${26 - ((v - min) / (max - min || 1)) * 22}`);
  spark.setAttribute('viewBox', '0 0 96 28');
  spark.innerHTML = `<polyline points="${pts.join(' ')}"/>`;
}

// Empty state preview: ?state=empty. Reuses the product handstand figure.
if (params.get('state') === 'empty') document.body.dataset.state = 'empty';
const emptyFigure = document.querySelector('.empty [data-handstand-cycle]');
if (emptyFigure && document.body.dataset.state === 'empty') {
  const {mountHandstandCycle, drawPose} = await import('/static/js/components/handstand-motion.js');
  // Reduced motion: a still pose at the top of the handstand instead of the loop.
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) drawPose(emptyFigure, 0.55);
  else mountHandstandCycle(emptyFigure);
}

const mobile = matchMedia('(max-width: 760px)');

// KPI carousel dots follow the snapped card.
const carousel = document.querySelector('[data-carousel]');
const dots = document.querySelector('[data-dots]');
if (carousel && dots) {
  dots.innerHTML = [...carousel.children].map(() => '<i></i>').join('');
  const mark = () => {
    const width = carousel.children[0].getBoundingClientRect().width + 12;
    const index = Math.round(carousel.scrollLeft / width);
    [...dots.children].forEach((d, i) => d.classList.toggle('on', i === index));
  };
  carousel.addEventListener('scroll', mark, {passive: true});
  mark();
}

// Segmented tabs + swipeable panels stay in sync.
const seg = document.querySelector('[data-seg]');
const panels = document.querySelector('[data-panels]');
if (seg && panels) {
  const tabsList = [...seg.querySelectorAll('[role=tab]')];
  const select = id => tabsList.forEach(t => {
    const on = t.getAttribute('aria-controls') === id;
    t.setAttribute('aria-selected', String(on));
    t.tabIndex = on ? 0 : -1;
    if (on) t.scrollIntoView({block: 'nearest', inline: 'nearest'});
  });
  tabsList.forEach(t => t.addEventListener('click', () => {
    const panel = document.getElementById(t.getAttribute('aria-controls'));
    const left = panel.offsetLeft - panels.children[0].offsetLeft;
    panels.scrollTo({left, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    select(panel.id);
  }));
  seg.addEventListener('keydown', e => {
    const i = tabsList.findIndex(t => t.getAttribute('aria-selected') === 'true');
    const next = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null;
    if (next === null || !tabsList[next]) return;
    tabsList[next].click(); tabsList[next].focus();
  });
  panels.addEventListener('scroll', () => {
    const step = panels.children[1].offsetLeft - panels.children[0].offsetLeft;
    const index = Math.round(panels.scrollLeft / step);
    const panel = panels.children[index];
    if (panel) select(panel.id);
  }, {passive: true});
}

// Profile accordion on phones; desktop shows every section.
const sections = [...document.querySelectorAll('.card[data-acc]')];
for (const [i, card] of sections.entries()) {
  const head = card.querySelector('.card-head');
  const body = document.createElement('div');
  body.className = 'acc-body';
  while (head.nextSibling) body.append(head.nextSibling);
  card.append(body);
  head.insertAdjacentHTML('beforeend', `<span class="acc-summary">${card.dataset.summary}</span><svg class="acc-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>`);
  const apply = () => {
    if (!mobile.matches) { card.dataset.open = 'true'; head.removeAttribute('role'); head.removeAttribute('tabindex'); head.removeAttribute('aria-expanded'); return; }
    head.setAttribute('role', 'button'); head.tabIndex = 0;
    if (!card.dataset.touched) card.dataset.open = String(i === 0);
    head.setAttribute('aria-expanded', card.dataset.open);
  };
  const toggle = () => { if (!mobile.matches) return; card.dataset.touched = '1'; card.dataset.open = String(card.dataset.open !== 'true'); apply(); };
  head.addEventListener('click', toggle);
  head.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
  mobile.addEventListener('change', apply);
  apply();
}
