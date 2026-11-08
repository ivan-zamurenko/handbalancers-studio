# П’ять handstand motion studies — 2026-11-08

Запит власника: показати5 різних анімацій і приміряти маленький центральний
індикатор із легким затемненням. Остаточний стиль/розташування не обрані.

Окреме статичне preview: /static/previews/handstand/index.html.
01 Перша спроба — тонка лінія, мах і корекція балансу.
02 Пружинка — округлий персонаж, пружний вихід, мікроемоція; рекомендація автора.
03 8-bit баланс — піксельний герой, дискретні пози.
04 Орбіта — геометрична фігура, коло, перехресний баланс.
05 Тихий баланс — плавний straddle press, пауза, дихаюче тло.

Рухи — локальні SVG/CSS; уточнений01 використовує SVG+JS (handstand-cycle.md); жодних бібліотек, API, зовнішніх ресурсів чи
зміни поточного runtime loader. Native dialog показує centre/corner placement;
навіть corner у цій примірці modal — це порівняння вигляду, не інтеграція
фонового завантаження. Escape/close повертають focus. Пауза, light/dark,
mobile, prefers-reduced-motion (з ручним opt-in playback).

Рекомендація: центр+scrim для дії, що потребує очікування, corner для background.
Після вибору власника окремо підключити конкретний варіант і визначити blocking
операції. Не перехоплювати всі фонoві session refresh повноекранним loader.

overview.gif:8.2s/10fps browser-rendered motion contact sheet, scaled924px;
overview.png:статичний огляд. Це preview artifacts, не runtime assets loader.

RED:3 browser scenarios failed (preview404, no cards/buttons).
GREEN:3 scenarios passed —5 cards, both themes390/1440, all motions/pause,
all5 modal previews, centre/corner, native Escape/focus, reduced-motion/no API.
Visual:desktop dark + central preview, mobile light. JS errors0 на локальному
preview. Read-only review без блокерів. Next: вибір власником стилю/placement.
