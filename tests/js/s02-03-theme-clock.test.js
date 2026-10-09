import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { createThemeController, resolveAutoTheme } from '../../server/static/js/state/theme.js';

const bootSource = readFileSync('server/static/js/theme-boot.js', 'utf8');
const shellSource = readFileSync('server/templates/shared/base.html', 'utf8');

function makeHarness({ start = '2026-10-09T06:59:00', storage } = {}) {
  let current = new Date(start);
  let timerCallback;
  let mediaChange;
  const listeners = new Map();
  const form = { value: 'unsaved workout note' };
  const root = {
    dataset: { theme: 'dark', themeStorageKey: 'studio:theme:guest' },
    style: { colorScheme: 'dark' },
    form,
  };
  const document = {
    visibilityState: 'visible',
    addEventListener(name, listener) {
      const group = listeners.get(name) || new Set();
      group.add(listener);
      listeners.set(name, group);
    },
    removeEventListener(name, listener) {
      listeners.get(name)?.delete(listener);
    },
  };
  const values = new Map();
  const localStorage = storage || {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); },
  };
  const controller = createThemeController({
    root,
    storage: localStorage,
    now: () => current,
    documentObject: document,
    setIntervalFunction(callback, delay) {
      assert.equal(delay, 60_000);
      timerCallback = callback;
      return 1;
    },
    clearIntervalFunction() {},
    windowObject: {
      matchMedia() {
        return {
          addEventListener(name, listener) {
            if (name === 'change') mediaChange = listener;
          },
          removeEventListener() {},
        };
      },
    },
  });

  return {
    root,
    form,
    controller,
    values,
    setClock(value) { current = new Date(value); },
    tick() { timerCallback(); },
    changeSystemPreference() { mediaChange(); },
    dispatch(name, visibilityState = 'visible') {
      document.visibilityState = visibilityState;
      for (const listener of listeners.get(name) || []) listener();
    },
  };
}

function runBoot({ preference = null, instant, blockedStorage = false } = {}) {
  const root = {
    dataset: { theme: 'dark', themeStorageKey: 'studio:theme:guest' },
    style: { colorScheme: 'dark' },
  };
  const storage = {
    getItem() {
      if (blockedStorage) throw new Error('storage unavailable');
      return preference;
    },
  };
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : [instant])); }
  }
  vm.runInNewContext(bootSource, {
    document: { documentElement: root },
    window: { localStorage: storage },
    Date: FixedDate,
  });
  return root;
}

test('auto_boundaries: 07:00 through 19:59 is light', () => {
  for (const [instant, expected] of [
    ['2026-10-09T06:59:00', 'dark'],
    ['2026-10-09T07:00:00', 'light'],
    ['2026-10-09T19:59:00', 'light'],
    ['2026-10-09T20:00:00', 'dark'],
  ]) {
    assert.equal(resolveAutoTheme(new Date(instant)), expected, instant);
    const root = runBoot({ instant: new Date(instant) });
    assert.equal(root.dataset.theme, expected, `boot ${instant}`);
    assert.equal(root.style.colorScheme, expected, `color scheme ${instant}`);
  }
});

test('manual_wins: clock and system preference changes do not override a manual choice', () => {
  const harness = makeHarness();
  harness.controller.setPreference('light');
  harness.setClock('2026-10-09T23:00:00');
  harness.tick();
  harness.changeSystemPreference();
  harness.dispatch('visibilitychange');
  assert.equal(harness.root.dataset.theme, 'light');
  assert.equal(harness.values.get('studio:theme:guest'), 'light');
  harness.controller.destroy();
});

test('blocked_storage: controller and early boot continue using device time', () => {
  const storage = {
    getItem() { throw new Error('storage unavailable'); },
    setItem() { throw new Error('storage unavailable'); },
  };
  const harness = makeHarness({ start: '2026-10-09T12:00:00', storage });
  assert.equal(harness.root.dataset.theme, 'light');
  assert.doesNotThrow(() => harness.controller.setPreference('dark'));
  assert.equal(harness.root.dataset.theme, 'dark');
  assert.equal(runBoot({ instant: new Date('2026-10-09T12:00:00'), blockedStorage: true }).dataset.theme, 'light');
  harness.controller.destroy();
});

test('active_workout_hold: automatic changes wait; manual changes are immediate', () => {
  const harness = makeHarness();
  harness.controller.setWorkoutActive(true);
  harness.setClock('2026-10-09T07:00:00');
  harness.tick();
  assert.equal(harness.root.dataset.theme, 'dark');

  harness.controller.setPreference('light');
  assert.equal(harness.root.dataset.theme, 'light');
  harness.controller.setPreference('auto');
  harness.setClock('2026-10-09T20:00:00');
  harness.tick();
  assert.equal(harness.root.dataset.theme, 'light');
  harness.controller.setWorkoutActive(false);
  assert.equal(harness.root.dataset.theme, 'dark');
  harness.controller.destroy();
});

test('clock_resume: visibility and boot reconcile time without mutating form state', () => {
  const harness = makeHarness({ start: '2026-10-09T19:59:00' });
  assert.equal(harness.root.dataset.theme, 'light');
  harness.setClock('2026-10-09T20:01:00');
  harness.dispatch('visibilitychange', 'hidden');
  assert.equal(harness.root.dataset.theme, 'light');
  harness.dispatch('visibilitychange', 'visible');
  assert.equal(harness.root.dataset.theme, 'dark');
  assert.equal(harness.form.value, 'unsaved workout note');
  assert.equal(runBoot({ instant: new Date('2026-10-09T20:01:00') }).dataset.theme, 'dark');
  harness.controller.destroy();
});

test('boot runs before theme CSS and carries the server CSP nonce', () => {
  const boot = shellSource.indexOf('/static/js/theme-boot.js');
  const css = shellSource.indexOf('/static/css/tokens.css');
  assert.ok(boot >= 0 && boot < css);
  assert.match(shellSource, /nonce="\{\{ csp_nonce/);
  assert.match(shellSource, /\/static\/js\/state\/theme\.js/);
});