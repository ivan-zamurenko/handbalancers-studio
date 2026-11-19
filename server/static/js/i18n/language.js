// Jinja supplies public copy pairs. Translate text/labels, never replace form nodes or values.
const source = document.getElementById('page-translations');
const pairs = source ? JSON.parse(source.textContent) : [];
const dictionaries = {uk: new Map(), en: new Map()};
for (const [uk,en] of pairs) {
  dictionaries.uk.set(en,uk); dictionaries.en.set(uk,en);
}
const skip = 'script,style,textarea,input,[contenteditable],[data-acc-summary]';
const attributes = new Set(['aria-label','title','placeholder','alt','content']);

function translated(value, dictionary) {
  const core = value.trim();
  if (dictionary.has(core)) return value.replace(core,dictionary.get(core));
  // Navigation arrows and the document title surround a translated label.
  for (const prefix of ['← ', 'Handbalancer’s Studio — ']) {
    if (core.startsWith(prefix) && dictionary.has(core.slice(prefix.length))) {
      return value.replace(core,prefix+dictionary.get(core.slice(prefix.length)));
    }
  }
  for (const suffix of [' — Handbalancer’s Studio', ' · Handbalancer’s Studio']) {
    if (core.endsWith(suffix) && dictionary.has(core.slice(0,-suffix.length))) {
      return value.replace(core,dictionary.get(core.slice(0,-suffix.length))+suffix);
    }
  }
  return value;
}

export function setLanguage(language, {updateURL = true} = {}) {
  if (!['uk','en'].includes(language)) return;
  const previous = document.documentElement.lang;
  if (previous !== language) {
    const dictionary = dictionaries[language];
    const walker = document.createTreeWalker(document.documentElement,NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.parentElement?.closest(skip)) node.nodeValue = translated(node.nodeValue,dictionary);
    }
    for (const element of document.querySelectorAll('*')) {
      if (element.closest('script,style,textarea,input[type=password],[contenteditable]')) continue;
      for (const attribute of [...element.attributes]) {
        if (attributes.has(attribute.name) || attribute.name.startsWith('data-')) {
          const next = translated(attribute.value,dictionary);
          if (next !== attribute.value) element.setAttribute(attribute.name,next);
        }
      }
    }
    document.documentElement.lang = language;
  }
  for (const link of document.querySelectorAll('a[href]')) {
    const url = new URL(link.href,location.href);
    if (url.origin !== location.origin) continue;
    if (link.closest('.locale-nav,.language-switch')) {
      if (link.lang === language) link.setAttribute('aria-current','page');
      else link.removeAttribute('aria-current');
    } else if (url.searchParams.has('lang')) {
      url.searchParams.set('lang',language);
      link.setAttribute('href',url.pathname+url.search+url.hash);
    }
  }
  if (updateURL) {
    const url = new URL(location.href);
    url.searchParams.set('lang',language);
    history.replaceState(history.state,'',url.pathname+url.search+url.hash);
  }
  try {localStorage.setItem('studio:locale',language);} catch { /* Display works without storage. */ }
  document.dispatchEvent(new CustomEvent('studio:language-changed',{detail:language}));
}

document.addEventListener('click',event=>{
  const link = event.target.closest?.('.locale-nav a[lang],.language-switch a[lang]');
  if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  setLanguage(link.lang);
  if (!link.getClientRects().length) document.querySelector('[data-menu-toggle]')?.focus();
});
document.addEventListener('studio:language-select',event=>setLanguage(event.detail));
// OAuth returns without a lang query. Restore only display preference, never identity or form data.
if (!new URL(location.href).searchParams.has('lang')) {
  try {const saved=localStorage.getItem('studio:locale'); if(saved) setLanguage(saved);} catch { /* Optional. */ }
}
