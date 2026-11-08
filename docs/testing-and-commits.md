# TDD, размер задач и Git

## Что считается одной задачей
Одна проверяемая ответственность и одна основная причина изменения. Хороший пример: «отвергать повторное применение stale preview». Плохой: «написать клиентский кабинет». Карточка перечисляет поведение, test file, allowed paths, API/DDL и commit subject. Если diff требует двух независимо полезных поведений, создать A/B subtasks с исходной dependency и не менять продукт.

Ориентир review — 100–300 строк содержательного кода, не жёсткий лимит. При >400 строках исполняемого кода или >8 файлах agent должен оценить деление и записать причину. Migration+model+tests одного инварианта могут честно быть больше. Lockfiles, исходный import handoff и generated manifests считать отдельно; не дробить логическую атомарность только ради цифры.

## Red → Green → Refactor
1. Прочитать конечный сценарий, определить внешний observable результат и негативный случай.
2. Написать минимальный тест на публичный service/API или DB constraint. Не писать тест на строку реализации.
3. Запустить targeted command, убедиться в ожидаемом RED. Неподнятый Docker, отсутствующий пакет/синтаксическая ошибка harness не доказательство бизнес-RED. Missing symbol при bootstrap допустим только как создание контракта, затем довести до meaningful assertion.
4. Записать безопасное краткое evidence: команда, expected assertion, actual failure, причина.
5. Реализовать только этот контракт; повторить test до GREEN. Не менять ожидания, убирая нужное поведение.
6. Refactor только под green, затем affected suite. Если код не менялся, не повторять одинаковый широкий suite без причины.
7. Review, commit, проверенный push, обновление состояния и следующая задача.

Сначала тесты во времени — не обязательно отдельный красный commit. Предпочитаем один green commit с тестами+кодом. RED логи не коммитить целиком: они могут содержать секреты. Summary evidence сохраняет факт команд, не внутренние рассуждения. Git history сама по себе не доказывает TDD; reviewer проверяет acceptance, отсутствие подгонки и воспроизводимость.

## Пирамида проверок
Pure unit — rules, measurements, time boundaries, entitlements, payload validation. Integration — настоящий PostgreSQL, transactions, constraints, role grants и две независимые connections для races. Auth integration — local Supabase, не auth shim как доказательство GoTrue/OAuth. Contract — HTTP status/schema/ownership/errors. Browser — критический путь и доступность, не каждый внутренний helper. External — отдельно реальный provider/staging и подтверждение владельца.

Не использовать SQLite как замену PostgreSQL для RLS/locking/partial index tests. Fakes только внешняя boundary; внутренний service не мокать в его собственном тесте. Browser tests test semantic user-visible behavior; role locators предпочтительнее привязки к CSS-позициям [S-PW]. Fixtures изолированы и удаляют только собственные тестовые данные [S-PYTEST].

Coverage не цель сама по себе. Все critical auth/owner/money/state/race ветки имеют явные сценарии; высокая line coverage не заменяет их. Mutation/property tests применять к рискованной policy, не ко всему ради процента.

## Git flow
Працюємо в наявному корені та погодженій гілці `task/execution-v4`; вона є default branch цього репозиторію. Не створювати новий вкладений проєкт. Назви task-гілок у старих картках — приклади, не вимога змінювати поточну гілку. Кожна картка має окремий green commit із subject картки. Нову гілку або merge використовувати в межах окремого доручення, без force push і без втрати попередньої історії.

Перед commit: `git status --short`, `git diff --check`, staged path review, targeted/affected tests. Добавлять явные пути (`git add path1 path2`), не слепое `git add .`. `git diff --cached` проверить на изменения вне задачи/секреты. Затем `git commit -m '<subject>'`.

После local green push только на уже подтверждённый remote+feature branch: `git push -u origin HEAD`. При отказе auth/network — local commit сохранён, push_pending; не придумывать remote SHA. Не force push, не bypass hooks, не reset чужих изменений. Merge виконується в явно погоджену цільову гілку за дорученням власника.

При каждом завершении: `git rev-parse HEAD`, status push/CI/review, список реально проверенных вещей, известный блокер, next task. SHA выводить после commit, а не вписывать в собственный создаваемый commit. Git global config пользователя не менять.

## Definition of Done
Acceptance соответствует approved decisions; expected RED наблюдался; GREEN targeted и affected suite; required DB migration/access/concurrency/browser checks; нет private data/placeholder production behavior; docs/state обновлены; review не содержит неустранённого критического дефекта; commit есть; push отдельно подтверждён или pending. Внешний gate не становится passed потому, что code done.

## Протокол ошибочного теста
Если acceptance ошибочен, записать mismatch с утверждённой спецификацией, исправить card/test отдельным видимым изменением и повторить RED. Не спрашивать владельца о технической опечатке; business-semantic изменение требует решения. Не добавлять skip/xfail для удобства без точной причины, owner/issue и срока снятия.
