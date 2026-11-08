import {drawPose, mountHandstandCycle} from './handstand-motion.js';

// A shared indicator for real work. Each caller owns one idempotent completion.
const indicator = globalThis.document?.querySelector('[data-loading-indicator]');
const pending = new Set();
let reveal;
let navigationTimer;
let finishNavigation;
let disposeMotion;
const figure = indicator?.querySelector('[data-handstand-cycle]');
const motionPreference = indicator ? matchMedia('(prefers-reduced-motion: reduce)') : null;

function syncMotion() {
  disposeMotion?.();
  disposeMotion = undefined;
  if (!figure || indicator.hidden) return;
  if (motionPreference.matches) drawPose(figure, .58);
  else disposeMotion = mountHandstandCycle(figure);
}

function hide() {
  indicator.hidden = true;
  disposeMotion?.();
  disposeMotion = undefined;
}

export function beginLoading() {
  if (!indicator) return () => {};
  const token = {};
  pending.add(token);
  if (pending.size === 1) {
    reveal = setTimeout(() => { indicator.hidden = false; syncMotion(); }, 180);
  }
  return () => {
    if (!pending.delete(token) || pending.size) return;
    clearTimeout(reveal);
    hide();
  };
}

export function beginNavigation() {
  finishNavigation?.();
  clearTimeout(navigationTimer);
  finishNavigation = beginLoading();
  // A cancelled browser navigation has no reliable completion event.
  navigationTimer = setTimeout(finishNavigation, 10000);
}

function reset() {
  clearTimeout(reveal);
  clearTimeout(navigationTimer);
  pending.clear();
  hide();
}

if (indicator) {
  motionPreference.addEventListener('change', syncMotion);
  if (document.readyState !== 'complete') {
    const finish = beginLoading();
    window.addEventListener('load', finish, {once:true});
  }
  window.addEventListener('pagehide', reset);
  window.addEventListener('pageshow', event => { if (event.persisted) reset(); });
  document.addEventListener('click', event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest?.('a[href]');
    if (!link || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    const target = new URL(link.href, location.href);
    if (target.origin !== location.origin || !['http:', 'https:'].includes(target.protocol)) return;
    if (link.getAttribute('href').startsWith('#') ||
        (target.pathname === location.pathname && target.search === location.search && target.hash)) return;
    setTimeout(() => { if (!event.defaultPrevented) beginNavigation(); }, 0);
  });
}
