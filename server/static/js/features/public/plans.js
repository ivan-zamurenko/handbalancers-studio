// Presentation preference only. Never grants a subscription or performs a payment.
const names = { essential: 'Essential', plus: 'Plus', pro: 'Pro', 'pro-plus': 'Pro+' };
const storageKey = 'studio:public:plan';
const english = document.documentElement.lang === 'en';
const radios = [...document.querySelectorAll('input[name="plan"]')];
const button = document.querySelector('[data-continue-plan]');
const status = document.querySelector('[data-storage-status]');
let canStore = true;
let selected = 'plus';
try {
  const saved = localStorage.getItem(storageKey);
  if (Object.hasOwn(names, saved)) selected = saved;
} catch { canStore = false; }

if (button) button.disabled = false;

function render() {
  for (const radio of radios) radio.checked = radio.value === selected;
  if (button) button.textContent = `${english ? 'Continue with' : 'Продовжити з'} ${names[selected]}`;
  const message = document.querySelector('[data-selection-message]');
  if (message) message.textContent = canStore
    ? `${english ? 'Your choice in this browser:' : 'Ваш вибір у цьому браузері:'} ${names[selected]}.`
    : `${english ? 'Current choice:' : 'Поточний вибір:'} ${names[selected]}.`;
  if (status) status.textContent = canStore ? '' : (english
    ? 'Browser storage is disabled. Your choice lasts until you leave this page.'
    : 'Локальне збереження вимкнене. Вибір діє до закриття цієї сторінки.');
}
for (const radio of radios) radio.addEventListener('change', () => {
  if (!Object.hasOwn(names, radio.value)) return;
  selected = radio.value;
  try { localStorage.setItem(storageKey, selected); } catch { canStore = false; }
  render();
});
render();
