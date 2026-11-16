import assert from 'node:assert/strict';
import test from 'node:test';
import { accountThemeKey, createThemeController } from '../../server/static/js/state/theme.js';
import { clearAccountState } from '../../server/static/js/state/session.js';

function memoryStorage() {
  const map = new Map();
  return {
    get length() { return map.size; },
    key: index => [...map.keys()][index] ?? null,
    getItem: key => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: key => map.delete(key),
  };
}

function controller(storage, storageKey) {
  const root = { dataset: { theme: 'light' }, style: {} };
  const noon = () => new Date('2026-11-16T12:00:00');
  return { root, theme: createThemeController({ root, storage, storageKey, now: noon,
    documentObject: null, windowObject: null, setIntervalFunction: null }) };
}

test('local_theme_account_isolation', () => {
  const storage = memoryStorage();
  globalThis.localStorage = storage;
  globalThis.sessionStorage = memoryStorage();
  try {
    controller(storage, 'studio:theme:guest').theme.setPreference('light');
    const first = controller(storage, accountThemeKey('account-a'));
    first.theme.setPreference('dark');
    assert.equal(storage.getItem('studio:account:account-a:theme'), 'dark');
    assert.equal(storage.getItem('studio:theme:guest'), 'light', 'account theme must not leak to guest');

    clearAccountState('account-a');
    const second = controller(storage, accountThemeKey('account-b'));
    assert.equal(second.theme.getPreference(), 'auto');
    assert.equal(second.root.dataset.theme, 'light', 'previous account dark theme not applied');
    assert.equal(storage.getItem('studio:account:account-a:theme'), null);
    assert.throws(() => accountThemeKey(''), TypeError);
  } finally {
    delete globalThis.localStorage;
    delete globalThis.sessionStorage;
  }
});
