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
