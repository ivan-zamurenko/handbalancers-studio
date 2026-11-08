import {drawPose, mountHandstandCycle} from './handstand-motion.js';

const indicator = globalThis.document?.querySelector('[data-loading-indicator]');
const navigation = globalThis.document?.querySelector('[data-loading-navigation]');
const figure = indicator?.querySelector('[data-handstand-cycle]');
const motionPreference = indicator ? matchMedia('(prefers-reduced-motion: reduce)') : null;
const channels = new Map([
  ['screen', {element:indicator, delay:500, tokens:new Set(), shown:false}],
  ['navigation', {element:navigation, delay:180, tokens:new Set(), shown:false}],
]);
const buttons = new Map();
const deferredClicks = new Set();
let disposeMotion, navigationTimer, finishNavigation;

function syncMotion() {
  disposeMotion?.();
  disposeMotion = undefined;
  if (!figure || indicator.hidden) return;
  if (motionPreference.matches) drawPose(figure, .58);
  else disposeMotion = mountHandstandCycle(figure);
}

function render() {
  const screen = channels.get('screen').shown;
  if (indicator && indicator.hidden === screen) {
    indicator.hidden = !screen;
    syncMotion();
  }
  if (navigation) navigation.hidden = screen || !channels.get('navigation').shown;
}

function restoreButton(button, state) {
  clearTimeout(state.timer);
  if (state.shown) button.replaceChildren(...state.nodes);
  button.classList.remove('is-loading');
  if (state.busy === null) button.removeAttribute('aria-busy');
  else button.setAttribute('aria-busy', state.busy);
  buttons.delete(button);
}

// Cosmetic feedback only: form/provider controllers continue to own disabled.
function beginButton(button, label) {
  if (!button?.replaceChildren) return () => {};
  let state = buttons.get(button);
  if (!state) {
    state = {tokens:new Set(), nodes:[...button.childNodes], busy:button.getAttribute('aria-busy'), shown:false};
    buttons.set(button, state);
    button.setAttribute('aria-busy', 'true');
    state.timer = setTimeout(() => {
      const spinner = document.createElement('span');
      spinner.className = 'button-spinner';
      spinner.setAttribute('aria-hidden', 'true');
      const text = label ?? button.dataset.pendingLabel;
      button.replaceChildren(spinner, ...(text ? [document.createTextNode(text)] : state.nodes));
      button.classList.add('is-loading');
      state.shown = true;
    }, 180);
  }
  const token = {};
  state.tokens.add(token);
  return () => {
    // An old completion after bfcache must not clear a newer button operation.
    if (buttons.get(button) !== state || !state.tokens.delete(token) || state.tokens.size) return;
    restoreButton(button, state);
  };
}

// Background work is silent. Visible feedback is an explicit caller choice.
export function beginLoading({mode='background', target, label} = {}) {
  if (mode === 'button') return beginButton(target, label);
  const channel = channels.get(mode);
  if (!channel?.element) return () => {};
  const token = {};
  channel.tokens.add(token);
  if (channel.tokens.size === 1) {
    channel.timer = setTimeout(() => {channel.shown=true; render();}, channel.delay);
  }
  return () => {
    if (!channel.tokens.delete(token) || channel.tokens.size) return;
    clearTimeout(channel.timer);
    channel.shown = false;
    render();
  };
}

export function beginNavigation() {
  finishNavigation?.();
  clearTimeout(navigationTimer);
  const finish = beginLoading({mode:'navigation'});
  finishNavigation = finish;
  // A cancelled browser navigation has no reliable completion event.
  navigationTimer = setTimeout(finish, 10000);
}

function reset() {
  clearTimeout(navigationTimer);
  finishNavigation = undefined;
  for (const timer of deferredClicks) clearTimeout(timer);
  deferredClicks.clear();
  for (const channel of channels.values()) {
    clearTimeout(channel.timer);
    channel.tokens.clear();
    channel.shown = false;
  }
  for (const [button,state] of buttons) restoreButton(button,state);
  render();
}

if (indicator) {
  motionPreference.addEventListener('change', syncMotion);
  if (document.readyState !== 'complete') {
    // Public pages are already server-rendered; remaining assets do not block them.
    const finish = beginLoading({mode:'navigation'});
    window.addEventListener('load', finish, {once:true});
  }
  window.addEventListener('pagehide', reset);
  window.addEventListener('pageshow', event => {if (event.persisted) reset();});
  document.addEventListener('click', event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest?.('a[href]');
    if (!link || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    const target = new URL(link.href, location.href);
    if (target.origin !== location.origin || !['http:', 'https:'].includes(target.protocol)) return;
    if (link.getAttribute('href').startsWith('#') ||
        (target.pathname === location.pathname && target.search === location.search && target.hash)) return;
    const timer = setTimeout(() => {
      deferredClicks.delete(timer);
      if (!event.defaultPrevented) beginNavigation();
    }, 0);
    deferredClicks.add(timer);
  });
}
