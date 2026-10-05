export const escapeHtml = (value = '') =>
  String(value).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
export const brand = () =>
  '<span class="brand" aria-label="Handbalancer’s Studio">h<span>.</span></span>';
export function statusBadge(state) {
  const statuses = {
    active: ['Активна', 'active'],
    expiring: ['Залишилось 5 днів', 'expiring'],
    inactive: ['Неактивна', 'inactive'],
  };
  const [label, kind] = statuses[state.subscriptionStatus] || statuses.inactive;
  return `<span class="status-badge ${kind}"><span class="status-dot" aria-hidden="true"></span>${label}</span>`;
}
const paths = {
  today: '<path d="M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  workout: '<path d="M5 7v10M2 9v6m17-8v10m3-8v6M5 12h14"/>',
  progress: '<path d="M4 4v16h16M7 15l4-5 4 3 5-8"/>',
  library:
    '<path d="M3 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H3Zm18 0h-6a3 3 0 0 0-3 3v14a4 4 0 0 1 4-3h5Z"/>',
  history: '<path d="M3 11a9 9 0 1 1 2.6 7M3 5v6h6m3-4v5l4 2"/>',
  profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  left: '<path d="m14 6-6 6 6 6"/>',
  right: '<path d="m10 6 6 6-6 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  play: '<path d="m8 4 12 8-12 8Z"/>',
  pause: '<path d="M8 4v16M16 4v16"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-4-4L5 15Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/>',
  trophy:
    '<path d="M8 3h8v8a4 4 0 0 1-8 0Zm0 2H4v3a4 4 0 0 0 4 4m8-7h4v3a4 4 0 0 1-4 4m-4 3v5m-4 1h8"/>',
  link: '<path d="m9 15 6-6m-5-3 2-2a5 5 0 0 1 7 7l-2 2m-3 5-2 2a5 5 0 0 1-7-7l2-2"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
};
export function icon(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.arrow}</svg>`;
}
export function formatDate(value) {
  const [y, m, d] = value.slice(0, 10).split('-');
  return `${d}.${m}.${y}`;
}
export const timerText = (seconds) =>
  `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
export const unitLabel = (unit) => (unit === 'sec' ? 'с' : 'повт.');
