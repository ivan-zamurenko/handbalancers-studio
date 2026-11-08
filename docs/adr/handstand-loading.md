# Центральний runtime loader — 2026-11-08

Пряма вказівка власника: анімація повинна працювати при завантаженні сайту.
Новий SVG та6.6s rig підключено через shared/base.html іloading.js.
Єдине джерело руху — static/js/components/handstand-motion.js; preview re-export.
Спільний handstand.css задає фігуру; loading.css — center card224px, легке
затемнення22%/blur2px, product tokens. Це status overlay, не dialog: фокус
не викрадається, pointer-events:none; блокування повторної форми лишається
обов’язком існуючих form guards.

PendingSet/idempotent done,180ms anti-flash, API body parsing іfinally,
помилки/abort/navigation/assets/bfcache збережені. При reveal створюється
controller; при hide/reset він dispose; reduced-motion static pose іlive
preference changes підтримані. Немає додаткового штучного очікування анімації.
Auth/provider logic не змінено; нових зовнішніх запитів іdependencies немає.

RED: новий runtime center test не знайшов .loading-card у старому corner loader.
Перший combined run16passed/1failed: ізольований сервер не має налаштованого
Google, тому кнопка відсутня. Тест виправлено через існуючий real-Jinja OAuth
UI fixture із синтетичною availability; не вмикали provider в runtime.
GREEN:68 full browser,40 JS,6 production motion tests; review без блокерів.
Перевірено local8000 /login під час реального, контрольовано затриманого
GET/health/live: показ по центру, рух, приховування після відповіді;
dark desktop/light mobile переглянуті. Cloud/OAuth реальні gates незмінні.

## Попередня версія

# Компактний handstand loading — 2026-11-08

Окремий явно погоджений запит власника після S03-08: маленька абстрактна людина,
яка намагається стати на руки, під час завантаження сторінки чи наступної дії.

Реалізація: inline SVG + CSS, наявні кольори теми, без пакетів/зображень/мережевих
провайдерів. Приблизно4.5KiB source для markup/style/controller. Фіксована маленька
картка внизу праворуч; pointer-events:none, без focus trap і блокування сторінки.
UK/EN, role=status, aria-live=polite, декоративний SVG, reduced motion = статична стійка.

Показ після180ms реального очікування. Set окремих ticket-ів і idempotent completion
не приховують індикатор, поки залишається інший запит. API client завершує ticket
після читання body; помилки/abort також проходять finally. Підключено наявні auth
request/session/logout, generic forms, початкове очікування window.load після
завантаження JS і звичайні same-origin переходи. Нові API дії мають використовувати
requestApi або beginLoading/finally, fetch глобально не підміняється.

Cancelled/defaultPrevented, hash-only, downloads, other tabs, external links не
вмикають автоматичний navigation indicator. Google redirect явно підключений.
pagehide/bfcache pageshow очищають tickets; для скасованого браузером переходу є
10s watchdog лише navigation-ticket. Це не timeout бізнес-запиту/не fake progress.
До першого HTML/JS сайт фізично не може показувати свій loader; працює браузер.

Перевірка:7 початкових RED через відсутній indicator;10 loader scenarios GREEN.
Два початкові навігаційні тестові запуски затримувалися через Playwright auto-wait
під час pending navigation. Вимогу не послаблено: MutationObserver встановлюється
до native click і через exposeFunction підтверджує старий DOM під час held route.
Виправлено також реальний edge case: microtask занадто рано бачить preventDefault;
перевірка перенесена в наступний task, додано native click cancellation regression.
Повна browser регресія61 passed, JS34, contracts35; visual mobile dark/desktop light
переглянуті вручну, усі4 theme/viewport поєднання перевірені браузером. Read-only
review без блокерів. No deployment, schema, secret або cloud configuration changes.
