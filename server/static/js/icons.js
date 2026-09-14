// Small original line drawings share a viewBox and stroke for consistent sizing.
const drawings = {
  handstand:
    '<circle cx="24" cy="33" r="3"/><path d="M24 28V17m0 0L17 5m7 12L31 5M24 25l-8 9-1 9m9-18 8 9 1 9M11 43h9m8 0h9"/>',
  strength:
    '<g transform="rotate(-35 24 24)"><rect x="9" y="13" width="6" height="22" rx="2"/><rect x="33" y="13" width="6" height="22" rx="2"/><path d="M15 21h18v6H15M9 18H5v12h4m30-12h4v12h-4"/></g>',
  mobility:
    '<circle cx="24" cy="10" r="3"/><path d="M24 16v14m0-8-11 5m11-5 11 5M24 30 8 39H3m21-9 16 9h5"/>',
  fitness:
    '<path d="M40 22c0 11-16 20-16 20S8 33 8 22a9 9 0 0 1 16-6 9 9 0 0 1 16 6Z"/><path d="M10 26h8l3-6 5 13 3-7h9"/>',
  clock:
    '<circle cx="24" cy="24" r="17"/><path d="M24 13v12l8 5M24 7v3m17 14h-3M24 41v-3M7 24h3"/>',
};
export const icon = (name) =>
  `<svg class="mono-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${drawings[name] || drawings.fitness}</svg>`;

const providerDrawings = {
  google:
    '<path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.89-1.74 2.98-4.31 2.98-7.36Z"/><path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.04.96-3.38.96-2.6 0-4.81-1.76-5.6-4.12H3.05v2.59A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.4 13.92a6 6 0 0 1 0-3.84V7.49H3.05a10 10 0 0 0 0 9.02Z"/><path fill="#EA4335" d="M12 5.96c1.47 0 2.79.51 3.82 1.51l2.87-2.87A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.95 5.49l3.35 2.59C7.19 7.72 9.4 5.96 12 5.96Z"/>',
  apple:
    '<path fill="currentColor" d="M17.05 12.54c.02 3.24 2.84 4.32 2.87 4.33-.02.08-.45 1.54-1.48 3.05-.9 1.3-1.82 2.6-3.29 2.63-1.44.03-1.9-.85-3.55-.85-1.65 0-2.17.82-3.53.88-1.42.05-2.49-1.42-3.4-2.72-1.85-2.67-3.26-7.55-1.36-10.85a5.28 5.28 0 0 1 4.46-2.71c1.4-.03 2.72.94 3.56.94.84 0 2.42-1.16 4.08-.99.7.03 2.67.29 3.94 2.15-.1.07-2.35 1.37-2.3 4.14ZM14.35 4.49c.75-.9 1.26-2.15 1.12-3.39-1.08.04-2.39.72-3.17 1.62-.7.8-1.31 2.08-1.15 3.3 1.2.09 2.44-.61 3.2-1.53Z"/>',
};

export const providerIcon = (name) =>
  `<svg class="provider-logo" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${providerDrawings[name]}</svg>`;

const socialDrawings = {
  x: '<path fill="currentColor" d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.64 7.584H.47l8.6-9.835L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"/>',
  youtube:
    '<path fill="currentColor" fill-rule="evenodd" d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8ZM9.6 15.6V8.4l6.3 3.6-6.3 3.6Z" clip-rule="evenodd"/>',
  instagram:
    '<g fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/></g><circle cx="17.5" cy="6.5" r="1.2" fill="currentColor"/>',
};

export const socialIcon = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${socialDrawings[name]}</svg>`;
