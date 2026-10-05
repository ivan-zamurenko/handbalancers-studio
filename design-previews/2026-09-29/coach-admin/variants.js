import { pendingClients, latestSession, trendFor } from './data.js';
import {
  icon,
  translator,
  localized,
  escapeHtml,
  button,
  tool,
  badge,
  dateText,
  unitText,
  directions,
  emptyState,
} from './ui.js';
import {
  clientHeading,
  clientTabs,
  clientContent,
  stats,
  chart,
  programView,
  reviewPanel,
  historyView,
  threeColumns,
  selection,
} from './components.js';

export const variants = [
  {
    id: '01',
    uk: 'Класична адмінка',
    en: 'The classic workspace',
    detail: [
      'Список клієнтів, профіль і знайома бічна навігація.',
      'Client directory, profile and familiar sidebar navigation.',
    ],
  },
  {
    id: '02',
    uk: 'Три колонки',
    en: 'Three columns',
    detail: [
      'Клієнт, тренування й перевірка завжди поруч.',
      'Client, workout and review stay side by side.',
    ],
  },
  {
    id: '03',
    uk: 'Черга перевірок',
    en: 'The review inbox',
    detail: [
      'Відео першим. Від поточної перевірки до наступної.',
      'Video first. Move from one review to the next.',
    ],
  },
  {
    id: '04',
    uk: 'Тижневий календар',
    en: 'The weekly calendar',
    detail: [
      'Уся студія на тижні, деталі заняття нижче.',
      'The studio week above, session detail below.',
    ],
  },
  {
    id: '05',
    uk: 'Журнал тренера',
    en: 'The coaching journal',
    detail: [
      'Історія виконань і рішень у хронологічній стрічці.',
      'Sessions and coaching decisions in a chronological feed.',
    ],
  },
  {
    id: '06',
    uk: 'Аналітичний стіл',
    en: 'The analysis desk',
    detail: [
      'Порівняння періодів і кожен підхід у центрі уваги.',
      'Period comparisons and individual sets take centre stage.',
    ],
  },
  {
    id: '07',
    uk: 'Програма в центрі',
    en: 'The program workspace',
    detail: [
      'Дерево тижнів, заняття й контекстна перевірка.',
      'A week tree, the session and contextual review.',
    ],
  },
  {
    id: '08',
    uk: 'Робоча таблиця',
    en: 'The working table',
    detail: [
      'Щільний список і профіль без втрати місця в таблиці.',
      'A dense directory with an adjacent client inspector.',
    ],
  },
  {
    id: '09',
    uk: 'Фокус на клієнті',
    en: 'Client focus',
    detail: [
      'Повноширинний профіль без постійного списку збоку.',
      'A full-width profile without a permanent client sidebar.',
    ],
  },
  {
    id: '10',
    uk: 'Клієнт і тренер',
    en: 'Client & coach',
    detail: [
      'Клієнтська програма й тренерська робота синхронно.',
      'The client program and coach tools, synchronised.',
    ],
  },
];

function clientSwitcher(state) {
  const text = translator(state);
  return `<label class="client-switcher"><span>${text('Клієнт', 'Client')}</span><select data-select="client" aria-label="${text('Вибрати клієнта', 'Select client')}">${state.data.clients.map((client) => `<option value="${client.id}" ${client.id === state.clientId ? 'selected' : ''}>${escapeHtml(client.name)}</option>`).join('')}</select></label>`;
}

function miniTrend(state, client) {
  const points = trendFor(client, 'handstand');
  if (!points.length)
    return `<span class="muted">${translator(state)('Немає даних', 'No data')}</span>`;
  const high = Math.max(40, ...points.map((point) => point.value));
  return `<svg class="mini-trend" viewBox="0 0 100 30" role="img" aria-label="${escapeHtml(`${client.name}: ${points[0].value} - ${points.at(-1).value} ${unitText(state, 'sec')}`)}"><polyline points="${points.map((point, index) => `${5 + index * 12.5},${28 - (point.value / high) * 24}`).join(' ')}" class="chart-actual"/></svg>`;
}

export function directory(state, brief = false) {
  const text = translator(state);
  const waiting = pendingClients(state.data).map((client) => client.id);
  const sort = state.sort || 'name';
  let clients = state.data.clients.filter(
    (client) =>
      client.name.toLowerCase().includes(state.search.toLowerCase()) &&
      (!state.pendingOnly || waiting.includes(client.id)),
  );
  clients = clients.toSorted((first, second) =>
    sort === 'activity'
      ? (latestSession(second)?.date || '').localeCompare(latestSession(first)?.date || '')
      : first.name.localeCompare(second.name),
  );
  if (brief && !state.search && !state.pendingOnly)
    clients = [state.data.clients[0], ...clients.filter((client) => client.id !== 'emma')].slice(
      0,
      3,
    );
  return `<section class="directory"><div class="section-head"><div><p class="eyebrow">${text('Студія', 'Studio')}</p><h2>${text('Клієнти', 'Clients')} <span class="count">${state.data.clients.length}</span></h2></div><div class="directory-tools"><label class="sr-only" for="client-search">${text('Пошук клієнта', 'Find a client')}</label><input id="client-search" type="search" placeholder="${text('Пошук клієнта', 'Find a client')}" value="${escapeHtml(state.search)}"><label class="sr-only" for="client-sort">${text('Сортування', 'Sort')}</label><select id="client-sort" data-select="sort"><option value="name" ${sort === 'name' ? 'selected' : ''}>${text('За ім’ям', 'By name')}</option><option value="activity" ${sort === 'activity' ? 'selected' : ''}>${text('За активністю', 'By activity')}</option></select></div></div><div class="table-scroll" tabindex="0" role="region" aria-label="${text('Таблиця клієнтів', 'Client table')}"><table><thead><tr><th>${text('Клієнт', 'Client')}</th><th>${text('Програма', 'Program')}</th><th>${text('Останнє заняття', 'Last session')}</th>${brief ? '' : `<th>${text('Стійка · с', 'Handstand · s')}</th>`}<th>${text('Перевірка', 'Review')}</th><th>${text('Тариф', 'Plan')}</th><th><span class="sr-only">${text('Відкрити', 'Open')}</span></th></tr></thead><tbody>${clients.map((client) => `<tr class="${client.id === state.clientId ? 'active-row' : ''}"><td><button type="button" class="table-person" data-action="select-client" data-id="${client.id}"><span class="avatar avatar-${client.id}">${client.initials}</span><span><strong>${escapeHtml(client.name)}</strong><small>${escapeHtml(directions(state)[client.direction])}</small></span></button></td><td>${client.program ? text('Баланс і сила', 'Balance & strength') : text('Не призначено', 'Unassigned')}</td><td>${latestSession(client) ? dateText(state, latestSession(client).date) : '-'}</td>${brief ? '' : `<td>${miniTrend(state, client)}</td>`}<td>${waiting.includes(client.id) ? badge(text('Нове відео', 'New video'), 'warning') : badge(client.sessions.length ? text('Без черги', 'No queue') : text('Новий клієнт', 'New client'))}</td><td>${badge(client.plan)}</td><td>${tool('select-client', `${text('Відкрити', 'Open')} ${client.name}`, 'right', `data-id="${client.id}"`)}</td></tr>`).join('') || `<tr><td colspan="7">${text('Нікого не знайдено', 'No matching clients')}</td></tr>`}</tbody></table></div>${brief ? `<div class="table-end">${button('clients', text('Усі клієнти', 'All clients'), 'arrow', '', 'quiet')}</div>` : ''}</section>`;
}

function classic(state) {
  return `<main id="workspace-main" class="classic-page" tabindex="-1">${directory(state, true)}<div class="classic-profile"><div class="profile-area">${clientHeading(state)}${clientTabs(state)}${clientContent(state)}</div>${reviewPanel(state)}</div></main>`;
}

function inbox(state) {
  const text = translator(state);
  const { entry } = selection(state);
  const queue = pendingClients(state.data);
  return `<div class="inbox-layout"><aside class="inbox-list"><div class="pane-heading"><h2>${text('Вхідні', 'Inbox')} <span class="count">${queue.length}</span></h2>${tool('clients', text('Клієнти', 'Clients'), 'profile')}</div><p class="inbox-date">${text('Цього тижня', 'This week')}</p>${queue.map((person) => `<button type="button" class="inbox-item ${person.id === state.clientId ? 'selected' : ''}" data-action="select-client" data-id="${person.id}"><span class="inbox-item-heading"><span class="avatar avatar-${person.id}">${person.initials}</span><strong>${escapeHtml(person.name)}</strong>${badge(person.plan)}</span><span class="inbox-item-body"><img src="assets/hero.webp" alt="" width="72" height="58"><span>${text('Стійка біля стіни', 'Wall handstand')}<small>${text('28 вер. · 3 підходи', '28 Sep · 3 sets')}</small></span></span><span class="inbox-item-status">${badge(text('Очікує перевірки', 'Awaiting review'), 'warning')}${icon('right')}</span></button>`).join('') || emptyState(state, text('Чергу опрацьовано', 'Inbox cleared'))}<div class="inbox-footer">${button('clients', text('Усі клієнти', 'All clients'), 'profile', '', 'quiet')}</div></aside><main id="workspace-main" class="inbox-main" tabindex="-1">${clientHeading(state, true)}<div class="review-hero"><div class="section-head"><div><p class="eyebrow">${text('Відео до призначеної вправи', 'Assigned exercise video')}</p><h2>${entry ? escapeHtml(localized(state, entry.name)) : text('Немає відео', 'No video')}</h2></div>${badge(text('28 вер.', '28 Sep'))}</div><button type="button" class="video-preview wide-video" data-action="video" aria-label="${text('Відкрити демо-кадр', 'Open demo frame')}"><img src="assets/hero.webp" alt="${text('Ілюстрація, не запис клієнта', 'Illustration, not a client recording')}"><span class="demo-image-label">${text('ДЕМО-КАДР', 'DEMO FRAME')}</span><span class="play-button">${icon('play')}</span></button></div>${programView(state)}${chart(state, true)}</main>${reviewPanel(state)}</div>`;
}

function calendar(state) {
  const text = translator(state);
  const start = new Date('2026-09-28T12:00:00Z');
  start.setUTCDate(start.getUTCDate() + (state.weekOffset || 0) * 7);
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(start);
    date.setUTCDate(date.getUTCDate() + index);
    return date.toISOString().slice(0, 10);
  });
  return `<main id="workspace-main" class="calendar-page" tabindex="-1"><section class="calendar-section"><div class="section-head"><div><p class="eyebrow">${text('Календар студії', 'Studio calendar')}</p><h1>${dateText(state, days[0])} - ${dateText(state, days[6])}</h1></div><div class="calendar-controls">${tool('previous-week', text('Попередній тиждень', 'Previous week'), 'left')}${button('this-week', text('Цей тиждень', 'This week'))}${tool('next-week', text('Наступний тиждень', 'Next week'), 'right')}</div></div><div class="table-scroll" tabindex="0" role="region" aria-label="${text('Тижневі заняття', 'Weekly sessions')}"><table class="schedule"><thead><tr><th>${text('Клієнт', 'Client')}</th>${days.map((date, index) => `<th class="${index === 1 && !state.weekOffset ? 'today-column' : ''}">${text(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'][index], ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][index])}<strong>${date.slice(-2)}</strong></th>`).join('')}</tr></thead><tbody>${state.data.clients
    .map(
      (client) =>
        `<tr><td><button type="button" class="table-person" data-action="select-client" data-id="${client.id}"><span class="avatar avatar-${client.id}">${client.initials}</span><strong>${escapeHtml(client.name)}</strong></button></td>${days
          .map((date, dayIndex) => {
            const session = client.sessions.find((item) => item.date === date);
            const planned = client.program && [0, 2, 4].includes(dayIndex) && date > '2026-09-28';
            return `<td>${session || planned ? `<button type="button" class="calendar-session ${session ? 'done' : 'planned'} ${client.id === state.clientId && session?.date === '2026-09-28' ? 'chosen' : ''}" data-action="calendar-session" data-client="${client.id}" data-date="${date}"><span>${session ? icon('check') : icon('calendar')}${text('Заняття', 'Session')} ${['A', '', 'B', '', 'C'][dayIndex] || 'A'}</span><small>${session ? text('Завершено', 'Completed') : text('Заплановано', 'Planned')}</small></button>` : `<span class="calendar-empty">-</span>`}</td>`;
          })
          .join('')}</tr>`,
    )
    .join(
      '',
    )}</tbody></table></div></section><div class="calendar-detail"><div class="profile-area">${clientHeading(state, true)}${programView(state)}${chart(state, true)}</div>${reviewPanel(state)}</div></main>`;
}

function journal(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="journal-page" tabindex="-1"><header class="page-heading"><div><p class="eyebrow">${text('Записи тренера', 'Coaching records')}</p><h1>${text('Журнал', 'Journal')}</h1></div>${clientSwitcher(state)}</header>${clientHeading(state, true)}<div class="journal-columns"><div class="journal-feed"><div class="journal-month"><span>09</span><strong>${text('Вересень 2026', 'September 2026')}</strong></div>${historyView(state)}</div><aside class="journal-side">${chart(state)}${reviewPanel(state)}</aside></div></main>`;
}

export function periodComparison(state) {
  const text = translator(state);
  const { client } = selection(state);
  const points = trendFor(client, state.metric);
  const exercise = state.data.exercises.find((item) => item.id === state.metric);
  const end = Date.parse('2026-09-28');
  const day = 86400000;
  const current = points.filter(
    (point) => Date.parse(point.date) > end - 14 * day && Date.parse(point.date) <= end,
  );
  const previous = points.filter(
    (point) => Date.parse(point.date) > end - 28 * day && Date.parse(point.date) <= end - 14 * day,
  );
  const unit = unitText(state, exercise.unit);
  const mean = (values) =>
    values.length ? values.reduce((total, point) => total + point.value, 0) / values.length : null;
  const currentMean = mean(current);
  const previousMean = mean(previous);
  const ceiling = Math.ceil(Math.max(10, ...points.map((point) => point.value)) / 10) * 10;
  const coords = (values, offset) =>
    values
      .map(
        (point) =>
          `${45 + ((Date.parse(point.date) - (end - (27 - offset) * day)) / day / 13) * 635},${210 - (point.value / ceiling) * 174}`,
      )
      .join(' ');
  const number = (value) =>
    value === null
      ? '-'
      : new Intl.NumberFormat(state.locale, { maximumFractionDigits: 1 }).format(value);
  return `<section class="comparison-panel"><div class="section-head"><div><p class="eyebrow">${text('Рівні періоди · по 14 днів', 'Equal periods · 14 days each')}</p><h2>${text('Поточний і попередній', 'Current & previous')}</h2></div><label><span class="sr-only">${text('Вправа для порівняння', 'Exercise to compare')}</span><select data-select="metric">${state.data.exercises
    .slice(0, 3)
    .map(
      (item) =>
        `<option value="${item.id}" ${state.metric === item.id ? 'selected' : ''}>${escapeHtml(localized(state, item.name))}</option>`,
    )
    .join(
      '',
    )}</select></label></div><div class="period-stat-row"><div><span><i class="legend-line"></i>15 - 28 ${text('вер.', 'Sep')}</span><strong>${number(currentMean)} <small>${unit}</small></strong></div><div><span><i class="legend-line previous"></i>1 - 14 ${text('вер.', 'Sep')}</span><strong>${number(previousMean)} <small>${unit}</small></strong></div><p>${text('Середнє найкращих підходів', 'Mean of best sets')}<small>${text('Та сама вправа · обидві сторони · без ваги', 'Same exercise · both sides · bodyweight')}</small></p></div>${current.length && previous.length ? `<svg class="comparison-chart" viewBox="0 0 720 250" role="img" aria-label="${escapeHtml(`${localized(state, exercise.name)}: ${number(previousMean)} → ${number(currentMean)} ${unit}`)}">${[0, 1, 2, 3, 4].map((tick) => `<line x1="45" x2="692" y1="${210 - (tick / 4) * 174}" y2="${210 - (tick / 4) * 174}" class="chart-grid"/><text x="31" y="${214 - (tick / 4) * 174}" text-anchor="end">${(ceiling / 4) * tick}</text>`).join('')}<polyline class="comparison-previous" points="${coords(previous, 0)}"/><polyline class="chart-actual" points="${coords(current, 14)}"/>${[1, 4, 7, 10, 14].map((value) => `<text x="${45 + ((value - 1) / 13) * 635}" y="236" text-anchor="middle">${value}</text>`).join('')}</svg><div class="axis-caption">${text('День періоду · найкращий підхід,', 'Day of period · best set,')} ${unit}</div>` : emptyState(state, text('Недостатньо даних для двох періодів', 'Not enough data for two periods'))}<details class="comparison-data"><summary>${text('Точні значення', 'Exact values')}</summary><div class="table-scroll"><table><thead><tr><th>${text('Дата', 'Date')}</th><th>${text('Період', 'Period')}</th><th>${unit}</th></tr></thead><tbody>${[...previous, ...current].map((point) => `<tr><td>${dateText(state, point.date)}</td><td>${current.includes(point) ? text('Поточний', 'Current') : text('Попередній', 'Previous')}</td><td>${point.value}</td></tr>`).join('')}</tbody></table></div></details></section>`;
}

function analytics(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="analytics-page" tabindex="-1"><header class="page-heading"><div><p class="eyebrow">${text('Індивідуальна аналітика', 'Individual analytics')}</p><h1>${text('Прогрес у деталях', 'Progress in detail')}</h1></div>${clientSwitcher(state)}</header>${clientHeading(state, true)}<div class="analytics-grid"><div>${periodComparison(state)}${stats(state)}${programView(state)}</div><aside class="analytics-side">${chart(state, true)}${reviewPanel(state)}</aside></div></main>`;
}

function programTree(state) {
  const text = translator(state);
  const program = state.data.programs[0];
  return `<aside class="program-tree"><p class="eyebrow">${text('Програма', 'Program')}</p><h2>${escapeHtml(localized(state, program.name))}</h2><div class="tree-meta">${badge(text('4 тижні', '4 weeks'))}${badge(text('3 заняття / тиждень', '3 sessions / week'))}</div>${program.weeks.map((week, index) => `<details ${index === 3 ? 'open' : ''}><summary><span>${text('Тиждень', 'Week')} ${index + 1}</span>${icon('right')}</summary>${week.sessions.map((session, sessionIndex) => `<button type="button" class="tree-session ${index === 3 && sessionIndex === 0 ? 'active' : ''}" data-action="open-program-session" data-week="${index}" data-session="${sessionIndex}">${icon(sessionIndex === 0 ? 'check' : 'workout')}<span>${text('Заняття', 'Session')} ${['A', 'B', 'C'][sessionIndex]}</span><small>${session.rows.length}</small></button>`).join('')}</details>`).join('')}<div class="tree-bottom">${button('programs', text('Редагувати шаблон', 'Edit template'), 'edit')}</div></aside>`;
}

function programCentered(state) {
  return `<div class="program-layout">${programTree(state)}<main id="workspace-main" class="program-main" tabindex="-1">${clientHeading(state, true)}${clientTabs(state)}${state.tab === 'overview' || state.tab === 'program' ? `<div id="client-content" role="tabpanel" aria-labelledby="tab-${state.tab}">${programView(state)}${chart(state)}</div>` : clientContent(state)}</main>${reviewPanel(state)}</div>`;
}

function workingTable(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="working-table-page" tabindex="-1"><header class="page-heading"><div><p class="eyebrow">${text('Робочий список', 'Working directory')}</p><h1>${text('Усі клієнти', 'All clients')}</h1></div><label class="check-label"><input id="pending-filter" type="checkbox" ${state.pendingOnly ? 'checked' : ''}>${text('Лише з перевіркою', 'Awaiting review only')}</label></header><div class="working-table-grid"><div class="working-table-main">${directory(state)}<div class="table-summary"><span>${state.data.clients.length} ${text('клієнтів', 'clients')}</span><span>${pendingClients(state.data).length} ${text('очікують перевірки', 'awaiting review')}</span></div>${periodComparison(state)}</div><aside class="table-inspector">${clientHeading(state, true)}${chart(state, true)}${reviewPanel(state)}</aside></div></main>`;
}

function focusedClient(state) {
  return `<main id="workspace-main" class="focus-page" tabindex="-1"><div class="focus-heading">${clientHeading(state)}${clientSwitcher(state)}</div>${clientTabs(state)}<div class="focus-columns"><div class="focus-main">${clientContent(state)}</div><div class="focus-review">${reviewPanel(state)}</div></div></main>`;
}

function splitClient(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="split-page" tabindex="-1"><header class="split-header">${clientHeading(state, true)}${clientSwitcher(state)}</header><div class="split-columns"><section class="split-client"><div class="split-mode-title"><div>${icon('profile')}<h2>${text('Клієнт', 'Client')}</h2></div>${badge(text('Лише читання', 'Read only'))}</div><div class="client-week-label"><p class="eyebrow">${text('Твоя програма · тиждень 4', 'Your program · week 4')}</p><h2>${text('Баланс і сила', 'Balance & strength')}</h2><div class="week-pills">${['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'].map((day, index) => `<span class="${index === 0 ? 'active' : ''}">${text(day, ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][index])}</span>`).join('')}</div></div>${programView(state, true)}</section><section class="split-coach"><div class="split-mode-title"><div>${icon('edit')}<h2>${text('Тренер', 'Coach')}</h2></div>${tool('programs', text('Редагувати майбутню програму', 'Edit future program'), 'calendar')}</div><div class="split-coach-columns"><div class="split-analysis">${chart(state)}${stats(state)}<div class="split-context"><p class="eyebrow">${text('Контекст виконання', 'Attempt context')}</p><h3>${text('28 вересня · заняття A', '28 September · session A')}</h3><p>${text('Версія програми 1', 'Program version 1')}</p></div></div>${reviewPanel(state)}</div></section></div></main>`;
}

const renderers = {
  '01': classic,
  '02': threeColumns,
  '03': inbox,
  '04': calendar,
  '05': journal,
  '06': analytics,
  '07': programCentered,
  '08': workingTable,
  '09': focusedClient,
  10: splitClient,
};
export const renderVariant = (state) => (renderers[state.variant] || threeColumns)(state);

export function gallery(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="gallery" tabindex="-1"><header class="gallery-heading"><div><a href="?" class="gallery-brand">h<span>.</span></a><p class="eyebrow">Handbalancer's Studio / ${text('Робоче місце тренера', 'Coach workspace')}</p><h1>${text('Десять способів працювати', 'Ten ways to work')}</h1></div><div class="gallery-controls">${tool('theme', text('Змінити тему', 'Change theme'), 'today')}<button type="button" class="button" data-action="language">${state.locale === 'uk' ? 'EN' : 'UA'}</button><span class="gallery-stamp">${text('29 ВЕР 2026', '29 SEP 2026')}</span></div></header><div class="gallery-filter"><span>${text('Один клієнт. Однакові дані. Різні компонування.', 'One client. The same data. Different layouts.')}</span>${badge(text('Ізольовані макети', 'Isolated prototypes'))}</div><div class="gallery-grid">${variants.map((variant) => `<a class="concept-card" href="?variant=${variant.id}"><div class="concept-image"><img src="screenshots/${variant.id}-desktop.png" alt="${escapeHtml(`${variant.id}. ${variant[state.locale]}`)}" width="1440" height="1000" loading="lazy"></div><div class="concept-caption"><span class="concept-id">${variant.id}</span><div><h2>${escapeHtml(variant[state.locale])}</h2><p>${escapeHtml(variant.detail[state.locale === 'uk' ? 0 : 1])}</p></div>${icon('arrow')}</div></a>`).join('')}</div><footer class="gallery-footer"><span>${text('Усі клієнти й результати вигадані. Чинний застосунок не змінено.', 'All clients and results are synthetic. The live application is unchanged.')}</span><a href="overview.png">${text('Огляд усіх десяти', 'All ten at a glance')} ${icon('arrow')}</a></footer></main>`;
}
