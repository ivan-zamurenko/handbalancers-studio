# Повний цикл thin-line handstand — 2026-11-08

Власник уточнив варіант01: звичайна стійка на ногах → крок уперед → руки
на підлогу → мах і приєднання другої ноги у стійці → сход назад → вихідна поза.
Стиль — тонка лінія першого варіанта. Жодних зірок, орбіт або падінь.

Оновлено01 у gallery; окремий перегляд /static/previews/handstand/cycle.html.
Цикл8.2s, пауза у верхній точці та стоячи. Малий JS-контролер інтерполює
ключові пози; двосегментні руки/ноги мають сталі довжини. Долоні нерухомі
під час опори. SVG без зовнішніх залежностей, мережі чи даних користувача.

RAF зупиняється на pause/hidden tab, elapsed не стрибає при поверненні;
reduced-motion починається нерухомо; dialog clone має dispose (RAF/observer/listener).
Основний runtime loader/правила blocking overlay не змінено: це refinement
анімації у вже погодженій preview-задачі, placement ще не визначено остаточно.

RED:node --test tests/js/handstand-cycle.test.js — module missing.
GREEN:2 geometry tests (1001 samples: fixed lengths/floor/anchored hands/phases),
4 browser tests (gallery themes390/1440, live joint motion, pause, reduced-motion
на картці іclone, native dialogs/Escape/focus, dedicatedcycle.html).
Попередній CSS-only motionassert замінено перевіркою SVG+animationclocks, бо RAF
не присутній у getAnimations(); вимогу руху не послаблено.

Read-only review без блокерів; reviewer-requested RAF/reduced-motion іstandalone
smoke додані та пройшли. Шість ключових поз переглянуто покадрово;mobile light
central preview також. cycle.gif —123frames/15fps/8.2s, actual browser render;
overview.gif/png оновлено для gallery. Нових cloud/runtime dependencies немає.
