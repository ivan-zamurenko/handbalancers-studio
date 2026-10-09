const supportedLocales = new Set(['uk', 'en']);

function resolveLocale(locale) {
  const candidate = (locale || 'uk').trim().replaceAll('_', '-').toLowerCase().split('-', 1)[0];
  return supportedLocales.has(candidate) ? candidate : 'uk';
}

export function formatNumber(value, locale = 'uk', options) {
  return new Intl.NumberFormat(resolveLocale(locale), options).format(value);
}

export function formatDate(value, locale = 'uk', options) {
  return new Intl.DateTimeFormat(resolveLocale(locale), options).format(value);
}