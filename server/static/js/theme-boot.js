(function applyInitialTheme() {
  if (typeof document === 'undefined' || !document.documentElement) return;

  const root = document.documentElement;
  const storageKey = root.dataset.themeStorageKey || 'studio:theme:guest';
  let preference = 'auto';

  try {
    preference = window.localStorage.getItem(storageKey) || 'auto';
  } catch {
    preference = 'auto';
  }

  const now = new Date();
  const minuteOfDay = now.getHours() * 60 + now.getMinutes();
  const automaticTheme = minuteOfDay >= 7 * 60 && minuteOfDay < 20 * 60
    ? 'light'
    : 'dark';
  const theme = preference === 'light' || preference === 'dark'
    ? preference
    : automaticTheme;

  root.dataset.theme = theme;
  root.style.colorScheme = theme;
})();