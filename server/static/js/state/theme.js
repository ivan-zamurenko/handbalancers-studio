const validPreferences = new Set(['auto', 'light', 'dark']);
const guestStorageKey = 'studio:theme:guest';

// Signed-in theme lives in the account namespace so clearAccountState() removes it.
export function accountThemeKey(accountId) {
  if (typeof accountId !== 'string' || !accountId) throw new TypeError('Account id is required');
  return `studio:account:${accountId}:theme`;
}

export function resolveAutoTheme(date = new Date()) {
  const minuteOfDay = date.getHours() * 60 + date.getMinutes();
  return minuteOfDay >= 7 * 60 && minuteOfDay < 20 * 60 ? 'light' : 'dark';
}

function getBrowserStorage() {
  try {
    return globalThis.localStorage;
  } catch {
    return null;
  }
}

function readPreference(storage, key) {
  try {
    const value = storage?.getItem(key);
    return validPreferences.has(value) ? value : 'auto';
  } catch {
    return 'auto';
  }
}

function writePreference(storage, key, preference) {
  try {
    storage?.setItem(key, preference);
  } catch {
    return;
  }
}

function applyTheme(root, theme) {
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

export function createThemeController({
  root = typeof document === 'undefined' ? null : document.documentElement,
  storage,
  storageKey,
  now = () => new Date(),
  documentObject = typeof document === 'undefined' ? null : document,
  windowObject = typeof window === 'undefined' ? null : window,
  setIntervalFunction = globalThis.setInterval,
  clearIntervalFunction = globalThis.clearInterval,
} = {}) {
  if (!root) throw new Error('A theme root element is required');

  const storageArea = storage === undefined ? getBrowserStorage() : storage;
  let key = storageKey || root.dataset.themeStorageKey || guestStorageKey;
  let preference = readPreference(storageArea, key);
  let workoutActive = false;
  let pendingTheme = null;

  const refresh = () => {
    if (preference !== 'auto') return;

    const nextTheme = resolveAutoTheme(now());
    if (workoutActive) {
      pendingTheme = nextTheme;
      return;
    }

    pendingTheme = null;
    applyTheme(root, nextTheme);
  };

  const onVisibilityChange = () => {
    if (documentObject?.visibilityState === 'visible') refresh();
  };
  documentObject?.addEventListener?.('visibilitychange', onVisibilityChange);

  const mediaQuery = windowObject?.matchMedia?.('(prefers-color-scheme: dark)');
  mediaQuery?.addEventListener?.('change', refresh);

  const timerId = typeof setIntervalFunction === 'function'
    ? setIntervalFunction(refresh, 60_000)
    : null;

  refresh();

  return {
    getPreference: () => preference,
    refresh,
    setPreference(nextPreference) {
      if (!validPreferences.has(nextPreference)) {
        throw new TypeError('Theme preference must be auto, light, or dark');
      }

      preference = nextPreference;
      writePreference(storageArea, key, preference);
      pendingTheme = null;
      if (preference === 'auto') refresh();
      else applyTheme(root, preference);
    },
    // Switch between guest and account storage; a server value wins when supplied.
    useStorage(nextKey, serverPreference) {
      key = nextKey || guestStorageKey;
      preference = validPreferences.has(serverPreference)
        ? serverPreference
        : readPreference(storageArea, key);
      if (validPreferences.has(serverPreference)) writePreference(storageArea, key, preference);
      pendingTheme = null;
      if (preference === 'auto') refresh();
      else applyTheme(root, preference);
    },
    setWorkoutActive(active) {
      workoutActive = Boolean(active);
      if (!workoutActive && preference === 'auto') refresh();
    },
    destroy() {
      documentObject?.removeEventListener?.('visibilitychange', onVisibilityChange);
      mediaQuery?.removeEventListener?.('change', refresh);
      if (timerId !== null && typeof clearIntervalFunction === 'function') {
        clearIntervalFunction(timerId);
      }
    },
  };
}

if (typeof document !== 'undefined' && document.documentElement) {
  const controller = createThemeController();
  const root = document.documentElement;
  for (const toggle of document.querySelectorAll('[data-theme-control]')) {
    toggle.disabled = false;
    const sync = () => toggle.setAttribute('aria-pressed', String(root.dataset.theme === 'dark'));
    sync();
    toggle.addEventListener('click', () => {
      root.dataset.themeAnimated = 'true';
      controller.setPreference(root.dataset.theme === 'dark' ? 'light' : 'dark');
      sync();
      document.dispatchEvent(new CustomEvent('studio:theme-changed', {detail: controller.getPreference()}));
    });
  }
  document.addEventListener('studio:theme-select', event => {
    controller.setPreference(event.detail);
    document.dispatchEvent(new CustomEvent('studio:theme-changed', {detail: controller.getPreference()}));
  });
  document.addEventListener('studio:account', event => {
    const {id, preference} = event.detail || {};
    controller.useStorage(id ? accountThemeKey(id) : null, preference);
    for (const toggle of document.querySelectorAll('[data-theme-control]')) {
      toggle.setAttribute('aria-pressed', String(root.dataset.theme === 'dark'));
    }
  });
  document.addEventListener('studio:workout-state', event => {
    const active = typeof event.detail === 'boolean' ? event.detail : event.detail?.active;
    if (typeof active === 'boolean') controller.setWorkoutActive(active);
  });
}