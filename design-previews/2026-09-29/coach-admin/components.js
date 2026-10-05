import {
  latestSession,
  noteKey,
  findEntry,
  clientAssignment,
  trendFor,
  comparisonFor,
  pendingClients,
} from './data.js';
import {
  escapeHtml,
  icon,
  translator,
  localized,
  unitText,
  dateText,
  tool,
  button,
  badge,
  emptyState,
  directions,
} from './ui.js';

export function selection(state) {
  const client =
    state.data.clients.find((item) => item.id === state.clientId) || state.data.clients[0];
  const fallback = latestSession(client);
  if (!fallback) return { client, session: null, entry: null };
  if (
    state.entryId &&
    client.sessions.some((session) => session.entries.some((entry) => entry.id === state.entryId))
  ) {
    return findEntry(state.data, client.id, state.entryId);
  }
  return { client, session: fallback, entry: fallback.entries[0] };
}

export function noteDraft(state) {
  const { client, entry } = selection(state);
  if (!entry) return '';
  const key = `${noteKey(client.id, entry.id)}:${state.visibility}`;
  return (
    state.drafts[key] ?? state.data.notes[noteKey(client.id, entry.id)]?.[state.visibility] ?? ''
  );
}

export function clientList(state, compact = false) {
  const text = translator(state);
  const pending = pendingClients(state.data).map((client) => client.id);
  const clients = state.data.clients.filter(
    (client) =>
      client.name.toLowerCase().includes(state.search.toLowerCase()) &&
      (!state.pendingOnly || pending.includes(client.id)),
  );
  return `<aside class="client-list-pane" aria-label="${text('Клієнти', 'Clients')}">
    <div class="pane-heading"><h2>${text('Клієнти', 'Clients')} <span class="count">${state.data.clients.length}</span></h2>${tool('clients', text('Відкрити список', 'Open directory'), 'arrow')}</div>
    <div class="list-controls"><label class="sr-only" for="client-search">${text('Знайти клієнта', 'Find a client')}</label><input type="search" id="client-search" placeholder="${text('Пошук клієнта', 'Find a client')}" value="${escapeHtml(state.search)}"><label class="check-label"><input type="checkbox" id="pending-filter" ${state.pendingOnly ? 'checked' : ''}>${text('Очікують перевірки', 'Awaiting review')} <span class="count">${pending.length}</span></label></div>
    <div class="people-list">${clients.map((client) => `<button type="button" class="person-row ${client.id === state.clientId ? 'selected' : ''}" data-action="select-client" data-id="${client.id}" aria-pressed="${client.id === state.clientId}"><span class="avatar avatar-${client.id}">${client.initials}</span><span class="person-info"><strong>${escapeHtml(client.name)}</strong><small>${escapeHtml(directions(state)[client.direction])} <span class="middot">·</span> ${client.plan}</small></span>${pending.includes(client.id) ? `<span class="unread-dot" aria-label="${text('Нове відео', 'New video')}"></span>` : ''}</button>`).join('') || `<p class="empty-search">${text('Нікого не знайдено', 'No matching clients')}</p>`}</div>
    ${compact ? '' : `<div class="list-footer"><span class="status-dot"></span>${text('Один тренер. Одна студія.', 'One coach. One studio.')}</div>`}
  </aside>`;
}

export function clientHeading(state, compact = false) {
  const text = translator(state);
  const { client } = selection(state);
  const access = {
    active: text('Активна', 'Active'),
    ending: text('До 4 жовт.', 'Until 4 Oct'),
    inactive: text('Неактивна', 'Inactive'),
  };
  return `<header class="client-heading ${compact ? 'compact-heading' : ''}"><div class="identity"><span class="avatar large avatar-${client.id}">${client.initials}</span><div><p class="eyebrow">${text('Профіль клієнта', 'Client profile')}</p><h1>${escapeHtml(client.name)}</h1><p class="identity-meta">${badge(client.plan)}<span class="access ${client.access}"><span class="status-dot"></span>${access[client.access]}</span><span>${client.timezone}</span></p></div></div><div class="heading-tools">${tool('client-details', text('Повна історія клієнта', 'Full client history'), 'history')}${tool('client-view', text('Вигляд клієнта', 'Client view'), 'profile')}${tool('assign', text('Призначити програму', 'Assign program'), 'calendar')}</div></header>`;
}

export function clientTabs(state) {
  const text = translator(state);
  const tabs = [
    ['overview', text('Огляд', 'Overview')],
    ['program', text('Програма', 'Program')],
    ['history', text('Історія', 'History')],
    ['videos', text('Відео', 'Videos')],
    ['notes', text('Нотатки', 'Notes')],
  ];
  return `<div class="tabs" role="tablist" aria-label="${text('Розділи клієнта', 'Client sections')}">${tabs.map(([id, label]) => `<button type="button" role="tab" id="tab-${id}" aria-controls="client-content" aria-selected="${state.tab === id}" tabindex="${state.tab === id ? '0' : '-1'}" data-action="tab" data-id="${id}">${label}</button>`).join('')}</div>`;
}

export function stats(state) {
  const text = translator(state);
  const { client } = selection(state);
  const points = trendFor(client, state.metric);
  const comparison = comparisonFor(points);
  const completed = client.sessions.filter((session) => session.status === 'completed');
  const minutes = completed.reduce((total, session) => total + session.minutes, 0);
  return `<dl class="stats-strip"><div><dt>${text('Останній найкращий', 'Latest best set')}</dt><dd>${comparison?.latest ?? '-'} <small>${points[0] ? unitText(state, points[0].unit) : ''}</small><span class="stat-detail">${text('Обрана вправа', 'Selected exercise')}</span></dd></div><div><dt>${text('Завершено', 'Completed')}</dt><dd>${completed.length} <small>${text('занять', 'sessions')}</small><span class="stat-detail">${text('За весь період', 'Across this period')}</span></dd></div><div><dt>${text('Час практики', 'Practice time')}</dt><dd>${Math.floor(minutes / 60)}<small> ${text('год', 'h')}</small> ${minutes % 60}<small> ${text('хв', 'm')}</small><span class="stat-detail">${text('Записаний час', 'Logged time')}</span></dd></div></dl>`;
}

export function chart(state, compact = false) {
  const text = translator(state);
  const { client } = selection(state);
  const exercise =
    state.data.exercises.find((item) => item.id === state.metric) || state.data.exercises[0];
  const all = trendFor(client, exercise.id);
  const points = state.range === 'recent' ? all.slice(-4) : all;
  const comparison = comparisonFor(points);
  const unit = unitText(state, exercise.unit);
  const top = `<div class="section-head"><div><p class="eyebrow">${text('Прогрес вправи', 'Exercise progress')}</p><h2>${escapeHtml(localized(state, exercise.name))}</h2></div><label class="range-control"><span class="sr-only">${text('Період', 'Period')}</span><select data-select="range" aria-label="${text('Період', 'Period')}"><option value="all" ${state.range === 'all' ? 'selected' : ''}>${text('4 тижні', '4 weeks')}</option><option value="recent" ${state.range === 'recent' ? 'selected' : ''}>${text('2 тижні', '2 weeks')}</option></select></label></div>`;
  if (points.length < 2)
    return `<section class="chart-panel">${top}${emptyState(state, text('Поки недостатньо даних', 'Not enough data yet'), text('Порівняння з’явиться після двох записаних занять.', 'A comparison needs two logged sessions.'))}</section>`;
  const ceiling =
    Math.ceil(Math.max(...points.flatMap((point) => [point.value, point.target])) / 10) * 10;
  const firstDate = Date.parse(points[0].date);
  const span = Date.parse(points.at(-1).date) - firstDate || 1;
  const pointX = (point) => 36 + ((Date.parse(point.date) - firstDate) / span) * 528;
  const pointY = (value) => 151 - (value / ceiling) * 125;
  const polyline = points.map((point) => `${pointX(point)},${pointY(point.value)}`).join(' ');
  const targetLine = points.map((point) => `${pointX(point)},${pointY(point.target)}`).join(' ');
  const delta = `${comparison.delta > 0 ? '+' : ''}${comparison.delta}`;
  return `<section class="chart-panel ${compact ? 'compact-chart' : ''}">${top}
    <div class="chart-meta"><strong class="${comparison.delta >= 0 ? 'positive' : 'negative'}">${delta} ${unit}</strong><span>${text('від першого запису', 'from first record')} <span class="chart-dates">${dateText(state, points[0].date)} - ${dateText(state, points.at(-1).date)}</span></span></div>
    <svg class="trend-chart" viewBox="0 0 600 185" role="img" aria-label="${escapeHtml(`${localized(state, exercise.name)}: ${comparison.first} - ${comparison.latest} ${unit}`)}">
      ${[0, 1, 2, 3, 4].map((tick) => `<line x1="36" y1="${pointY((ceiling / 4) * tick)}" x2="574" y2="${pointY((ceiling / 4) * tick)}" class="chart-grid"/><text x="24" y="${pointY((ceiling / 4) * tick) + 4}" text-anchor="end">${(ceiling / 4) * tick}</text>`).join('')}
      <polyline points="${targetLine}" class="chart-target"/><polyline points="${polyline}" class="chart-actual"/>
      ${points.map((point, index) => `<circle cx="${pointX(point)}" cy="${pointY(point.value)}" r="${index === points.length - 1 ? 5 : 3.5}" class="chart-point"/>${index % 2 === 0 || index === points.length - 1 ? `<text x="${pointX(point)}" y="176" text-anchor="middle">${point.date.slice(-2)}.09</text>` : ''}`).join('')}
    </svg><div class="chart-footer"><div class="legend"><span><i class="legend-line"></i>${text('Найкращий підхід', 'Best set')} · ${unit}</span><span><i class="legend-line target"></i>${text('Ціль', 'Target')}</span></div><details class="chart-data"><summary>${text('Дані', 'Data')}</summary><table><caption>${escapeHtml(localized(state, exercise.name))} · ${unit}</caption><thead><tr><th>${text('Дата', 'Date')}</th><th>${text('Факт', 'Actual')}</th><th>${text('Ціль', 'Target')}</th></tr></thead><tbody>${points.map((point) => `<tr><td>${dateText(state, point.date)}</td><td>${point.value}</td><td>${point.target}</td></tr>`).join('')}</tbody></table></details></div>
  </section>`;
}

export function programView(state, clientMode = false, sessionOverride = null) {
  const text = translator(state);
  const { client, session: current, entry: selected } = selection(state);
  const session = sessionOverride || current;
  if (!session) return emptyState(state, text('Програму ще не призначено', 'No program assigned'));
  const entries = session.entries.map((entry) =>
    clientMode ? clientAssignment(state.data, client.id, entry.id) : entry,
  );
  return `<section class="session-panel ${clientMode ? 'client-program' : ''}"><div class="section-head"><div><p class="eyebrow">${dateText(state, session.date)} <span class="middot">·</span> ${text('Заняття A', 'Session A')} <span class="middot">·</span> v${session.version}</p><h2>${escapeHtml(localized(state, session.title))}</h2></div>${badge(text('Завершено', 'Completed'), 'success')}</div>
    <div class="exercise-list">${entries.map((entry, index) => `<article class="exercise-row ${!clientMode && selected?.id === entry.id ? 'selected-exercise' : ''}" data-assignment="${entry.id}"><div class="exercise-row-top"><span class="exercise-number">${String(index + 1).padStart(2, '0')}</span><div class="exercise-description"><h3>${escapeHtml(localized(state, entry.name))}</h3><p>${entry.target.length} × ${entry.target[0]} ${unitText(state, entry.unit)} <span class="middot">·</span> ${text('відпочинок', 'rest')} ${entry.rest} ${text('с', 's')}</p></div>${clientMode ? '' : tool('select-entry', text('Відкрити вправу', 'Open exercise'), 'right', `data-id="${entry.id}"`)}</div><div class="set-results"><span class="set-label">${text('Факт', 'Actual')}</span>${entry.actual.map((value, setIndex) => `<span class="set-result" data-set="${setIndex}"><small>${setIndex + 1}</small><strong>${value ?? '-'}</strong><span>${unitText(state, entry.unit)}</span></span>`).join('')}${entry.video ? `<button type="button" class="video-link" data-action="${clientMode ? 'video' : 'select-entry'}" data-id="${entry.id}">${icon('play')}<span>${text('Відео', 'Video')}</span></button>` : ''}</div>${clientMode ? `<p class="exercise-cue">${escapeHtml(localized(state, entry.cue))}</p>${entry.note ? `<div class="client-note" data-client-note><strong>${text('Від тренера', 'From your coach')}</strong><p>${escapeHtml(entry.note)}</p></div>` : ''}` : ''}</article>`).join('')}</div>
  </section>`;
}

export function reviewPanel(state) {
  const text = translator(state);
  const { client, session, entry } = selection(state);
  if (!entry)
    return `<aside class="review-pane">${emptyState(state, text('Немає занять на перевірку', 'No sessions to review'))}</aside>`;
  const completed = state.data.reviews[noteKey(client.id, entry.id)] === 'completed';
  return `<aside class="review-pane" aria-label="${text('Перевірка вправи', 'Exercise review')}"><div class="pane-heading"><h2>${text('Перевірка', 'Review')}</h2>${badge(completed ? text('Перевірено', 'Reviewed') : text('Очікує', 'Pending'), completed ? 'success' : 'warning')}</div><div class="review-context"><strong>${escapeHtml(client.name)}</strong><span>${dateText(state, session.date)} <span class="middot">·</span> ${text('Заняття A', 'Session A')}</span><h3>${escapeHtml(localized(state, entry.name))}</h3></div>
    ${entry.video ? `<button type="button" class="video-preview" data-action="video" aria-label="${text('Відкрити демонстрацію перегляду', 'Open review demonstration')}"><img src="assets/hero.webp" width="1536" height="1024" alt="${text('Художня ілюстрація стійки, не відео клієнта', 'Artistic handstand illustration, not a client video')}"><span class="demo-image-label">${text('ДЕМО-КАДР', 'DEMO FRAME')}</span><span class="play-button">${icon('play')}</span><span class="video-source">YouTube ${icon('link')}</span></button>` : `<div class="video-unavailable">${icon('link')}<strong>${text('Без відеопосилання', 'No video link')}</strong></div>`}
    <form id="note-form"><div class="note-header"><label for="coach-note">${text('Нотатка до вправи', 'Exercise note')}</label><span class="draft-state" data-draft-state></span></div><div class="segmented" role="group" aria-label="${text('Видимість нотатки', 'Note visibility')}"><button type="button" data-action="visibility" data-id="client" aria-pressed="${state.visibility === 'client'}">${text('Клієнту', 'Client')}</button><button type="button" data-action="visibility" data-id="private" aria-pressed="${state.visibility === 'private'}">${text('Лише мені', 'Private')}</button></div><textarea id="coach-note" rows="4" maxlength="2000" placeholder="${text('Твій коментар до цього виконання…', 'Your feedback on this attempt…')}">${escapeHtml(noteDraft(state))}</textarea><button class="button save-note" type="submit">${icon('check')}<span>${text('Зберегти нотатку', 'Save note')}</span></button></form>
    <div class="review-actions">${button('complete-review', completed ? text('Перевірку завершено', 'Review complete') : text('Завершити перевірку', 'Complete review'), 'check', completed ? 'disabled' : '', 'primary')}${button('next-client', text('Наступний клієнт', 'Next client'), 'arrow', '', 'quiet')}</div>
  </aside>`;
}

export function historyView(state) {
  const text = translator(state);
  const { client } = selection(state);
  return `<section class="history-panel"><div class="section-head"><h2>${text('Історія тренувань', 'Training history')}</h2><span class="muted">${client.sessions.length} ${text('занять', 'sessions')}</span></div>${
    client.sessions.length
      ? client.sessions
          .toReversed()
          .map(
            (session, index) =>
              `<details class="history-entry" ${index === 0 ? 'open' : ''}><summary><span>${dateText(state, session.date)}</span><strong>${escapeHtml(localized(state, session.title))}</strong><span>${session.minutes} ${text('хв', 'min')}</span>${icon('right')}</summary>${programView(state, false, session)}</details>`,
          )
          .join('')
      : emptyState(state, text('Історія поки порожня', 'No history yet'))
  }</section>`;
}

export function clientContent(state) {
  const text = translator(state);
  let content = '';
  if (state.tab === 'overview') content = `${stats(state)}${chart(state)}${programView(state)}`;
  if (state.tab === 'program')
    content = `${futurePrograms(state)}<div class="program-banner"><div><p class="eyebrow">${text('Призначена програма', 'Assigned program')}</p><h2>${text('Баланс і сила', 'Balance & strength')}</h2></div>${button('programs', text('Редактор', 'Editor'), 'edit')}</div>${programView(state)}${chart(state, true)}`;
  if (state.tab === 'history') content = historyView(state);
  if (state.tab === 'videos') content = `${chart(state, true)}${programView(state)}`;
  if (state.tab === 'notes') {
    const { client } = selection(state);
    const notes = client.sessions.flatMap((session) =>
      session.entries
        .filter((entry) => state.data.notes[noteKey(client.id, entry.id)])
        .map((entry) => ({ session, entry, note: state.data.notes[noteKey(client.id, entry.id)] })),
    );
    content = `<section class="notes-list">${notes.length ? notes.map(({ session, entry, note }) => `<article><div class="section-head"><div><p class="eyebrow">${dateText(state, session.date)}</p><h3>${escapeHtml(localized(state, entry.name))}</h3></div>${tool('select-entry', text('Відкрити', 'Open'), 'right', `data-id="${entry.id}"`)}</div>${['client', 'private'].map((visibility) => (note[visibility] ? `<div class="saved-note">${badge(visibility === 'client' ? text('Клієнту', 'Client') : text('Лише мені', 'Private'))}<p>${escapeHtml(note[visibility])}</p></div>` : '')).join('')}</article>`).join('') : emptyState(state, text('Нотаток ще немає', 'No notes yet'))}</section>`;
  }
  return `<div id="client-content" role="tabpanel" aria-labelledby="tab-${state.tab}">${content}</div>`;
}

export function threeColumns(state) {
  return `<div class="three-columns">${clientList(state, true)}<main id="workspace-main" class="client-main" tabindex="-1">${clientHeading(state)}${clientTabs(state)}${clientContent(state)}</main>${reviewPanel(state)}</div>`;
}

export function shell(state, content) {
  const text = translator(state);
  const nav = [
    ['workspace', 'today', text('Огляд', 'Overview')],
    ['clients', 'profile', text('Клієнти', 'Clients')],
    ['reviews', 'check', text('Перевірки', 'Reviews')],
    ['programs', 'library', text('Програми', 'Programs')],
    ['exercises', 'workout', text('Вправи', 'Exercises')],
    ['settings', 'edit', text('Налаштування', 'Settings')],
  ];
  return `<header class="preview-toolbar"><button type="button" class="preview-home" data-action="gallery" aria-label="${text('Усі макети', 'All concepts')}">${icon('left')}<span>${text('Усі макети', 'All concepts')}</span></button><div class="variant-caption"><span class="variant-number">${state.variant}</span><strong>${escapeHtml(state.variantName)}</strong></div><span class="preview-disclaimer">${text('Демонстраційні дані', 'Synthetic data')}</span><div class="preview-tools">${tool('previous-variant', text('Попередній макет', 'Previous concept'), 'left')}${tool('next-variant', text('Наступний макет', 'Next concept'), 'right')}${tool('theme', text('Змінити тему', 'Change theme'), 'today')}<button type="button" class="locale-button" data-action="language" aria-label="${state.locale === 'uk' ? 'English' : 'Українська'}">${state.locale === 'uk' ? 'EN' : 'UA'}</button>${tool('reset', text('Скинути приклад', 'Reset demo'), 'history')}</div></header>
    <div class="app-frame variant-${state.variant}"><aside class="app-nav"><a class="brand-mark" href="?" aria-label="Handbalancer's Studio">h<span>.</span></a><nav aria-label="${text('Розділи студії', 'Studio navigation')}">${nav.map(([id, symbol, label]) => `<button type="button" data-action="${id}" class="nav-item ${state.page === id ? 'active' : ''}" ${state.page === id ? 'aria-current="page"' : ''} aria-label="${label}" title="${label}">${icon(symbol)}<span>${label}</span>${id === 'reviews' ? `<i class="nav-count">${pendingClients(state.data).length}</i>` : ''}</button>`).join('')}</nav><div class="coach-avatar" title="${text('Тренер', 'Coach')}">IZ</div></aside><div class="workspace"><header class="workspace-header"><div class="studio-wordmark">Handbalancer's Studio <span>/ ${text('Тренер', 'Coach')}</span></div><div class="workspace-header-actions"><span class="today-label">${text('Вівторок, 29 вересня', 'Tuesday, 29 September')}</span>${button('programs', text('Програми', 'Programs'), 'library')}</div></header>${content}</div></div>`;
}

export function clientPreview(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="client-preview-page" tabindex="-1"><div class="preview-client-bar">${button('workspace', text('До тренера', 'Back to coach'), 'left')}${badge(text('Вигляд клієнта · лише читання', 'Client view · read only'))}</div>${clientHeading(state, true)}${futurePrograms(state)}${programView(state, true)}</main>`;
}

export function futurePrograms(state) {
  const text = translator(state);
  return state.data.assignments
    .filter((assignment) => assignment.clientId === state.clientId)
    .map(
      (assignment) =>
        `<section class="future-program" data-future-assignment="${assignment.id}"><div class="section-head"><div><p class="eyebrow">${text('Початок', 'Starts')} ${dateText(state, assignment.startsOn)} · v${assignment.version.number}</p><h2>${escapeHtml(localized(state, assignment.version.name))}</h2></div>${badge(text('Майбутня програма', 'Future program'))}</div>${assignment.version.weeks.map((week, index) => `<details><summary>${text('Тиждень', 'Week')} ${index + 1}</summary>${week.sessions.map((session) => `<article><h3>${escapeHtml(session.name)}</h3>${session.rows.map((row) => `<div class="future-exercise"><span>${escapeHtml(localized(state, row.name))}</span><strong>${row.targets.join(' / ')} ${unitText(state, row.unit)}</strong></div>`).join('')}</article>`).join('')}</details>`).join('')}</section>`,
    )
    .join('');
}
