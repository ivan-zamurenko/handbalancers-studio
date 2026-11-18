// Phone navigation: a modal side panel. Works without JS via #site-menu (:target);
// with JS it adds focus management, Esc/backdrop close, scroll lock and inert content.
const toggle = document.querySelector('[data-menu-toggle]');
const menu = document.getElementById('site-menu');
const phone = matchMedia('(max-width: 780px)');
const background = () => [...document.querySelectorAll('main, footer, .skip-link, .header-inner > :not(#site-menu)')];
let previousInert = [];
let previousOverflow = '';
const focusable = () => [...menu.querySelectorAll('a[href]:not([tabindex="-1"]), button:not([disabled])')]
  .filter(element => element.offsetParent !== null || element === document.activeElement);

function isOpen() {
  return menu.dataset.open === 'true';
}

function open() {
  if (!phone.matches || isOpen()) return;
  menu.dataset.open = 'true';
  menu.setAttribute('role', 'dialog');
  menu.setAttribute('aria-modal', 'true');
  toggle.setAttribute('aria-expanded', 'true');
  previousOverflow = document.documentElement.style.overflow;
  document.documentElement.style.overflow = 'hidden';
  previousInert = background().map(element => [element, element.inert]);
  for (const [element] of previousInert) element.inert = true;
  document.addEventListener('keydown', onKey);
  menu.querySelector('.primary-nav a')?.focus();
}

function close({restoreFocus = true} = {}) {
  if (!isOpen()) return;
  menu.dataset.open = 'false';
  menu.removeAttribute('role');
  menu.removeAttribute('aria-modal');
  toggle.setAttribute('aria-expanded', 'false');
  document.documentElement.style.overflow = previousOverflow;
  for (const [element, inert] of previousInert) element.inert = inert;
  previousInert = [];
  document.removeEventListener('keydown', onKey);
  if (location.hash === '#site-menu') history.replaceState(null, '', location.pathname + location.search);
  if (restoreFocus) toggle.focus();
}

function onKey(event) {
  if (event.key === 'Escape') {
    event.preventDefault();
    close();
    return;
  }
  if (event.key !== 'Tab') return;
  const items = focusable();
  if (!items.length) return;
  const first = items[0], last = items.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  else if (!menu.contains(document.activeElement)) { event.preventDefault(); first.focus(); }
}

if (toggle && menu) {
  menu.dataset.open = 'false';
  toggle.addEventListener('click', event => {
    event.preventDefault();
    if (isOpen()) close(); else open();
  });
  toggle.addEventListener('keydown', event => {
    if (event.key === ' ') { event.preventDefault(); toggle.click(); }
  });
  for (const closer of menu.querySelectorAll('[data-menu-close], [data-menu-close-backdrop]')) {
    closer.addEventListener('click', event => { event.preventDefault(); close(); });
    closer.addEventListener('keydown', event => {
      if (event.key === ' ') { event.preventDefault(); closer.click(); }
    });
  }
  // Choosing a destination closes the panel; same-page anchors then scroll under the bar.
  menu.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (link && !link.matches('[data-menu-close], [data-menu-close-backdrop]')) close({restoreFocus: false});
  });
  phone.addEventListener('change', () => { if (!phone.matches) close({restoreFocus: false}); });
  document.addEventListener('studio:close-menu', () => close({restoreFocus: false}));
  // Opened through the no-JS fallback (#site-menu) before this script ran.
  if (location.hash === '#site-menu' && phone.matches) open();
}
