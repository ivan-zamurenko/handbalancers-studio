import { icon, escapeHtml } from './assets/studio-ui.js';

export { icon, escapeHtml };
export const translator = (state) => (uk, en) => (state.locale === 'uk' ? uk : en);
export const localized = (state, value) => value?.[state.locale] || value?.uk || '';
export const unitText = (state, unit) =>
  unit === 'sec' ? translator(state)('с', 's') : translator(state)('повт.', 'reps');
export const dateText = (state, date) =>
  new Intl.DateTimeFormat(state.locale === 'uk' ? 'uk-UA' : 'en-IE', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(`${date}T12:00:00Z`));

export function tool(action, label, symbol, attributes = '') {
  const visual = action === 'theme' ? '<span aria-hidden="true">◐</span>' : icon(symbol);
  return `<button type="button" class="icon-button" data-action="${action}" aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}" ${attributes}>${visual}</button>`;
}

export function button(action, label, symbol = '', attributes = '', kind = '') {
  return `<button type="button" class="button ${kind}" data-action="${action}" ${attributes}>${symbol ? icon(symbol) : ''}<span>${escapeHtml(label)}</span></button>`;
}

export function badge(label, kind = '') {
  return `<span class="badge ${kind}">${escapeHtml(label)}</span>`;
}

export function emptyState(state, title, detail = '') {
  return `<div class="empty-state">${icon('library')}<h3>${escapeHtml(title)}</h3>${detail ? `<p>${escapeHtml(detail)}</p>` : ''}</div>`;
}

export const directions = (state) => ({
  handstand: translator(state)('Стійка', 'Handstand'),
  strength: translator(state)('Сила', 'Strength'),
  mobility: translator(state)('Рухливість', 'Mobility'),
  fitness: translator(state)('Фізична форма', 'Fitness'),
});
