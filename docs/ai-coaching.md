# AI-супровід Studio: мінімальна архітектура й поетапне впровадження

Погоджено власником 2026-11-24. Статус: **план майбутньої реалізації**.
S00-09 оформлює цей документ і roadmap; це не готовий відеоаналіз.
Фактичний стан карток — `.workflow/state.json`. Пріоритет рішень —
[decisions.md](decisions.md); спільні правила — [contracts.md](contracts.md).

## Продукт і межі

Це AI-супровід у чинному Handbalancer’s Studio, не новий продукт.
Шлях: програма → приклад вправи → виконання → відео одного підходу →
вимірювання → пояснення → рекомендації → адаптація майбутніх занять →
перевірка прогресу. Перша повна методика — стійка на руках збоку.

Зберігаємо одну поточну основну програму, календар, каталог, власника,
історію, чинні тарифи й роль тренера. Один поточний контрольний ролик на
`session_exercise`; він може позначати обраний `captured_set_log_id`.
Не вводимо відео кожного підходу чи самостійний аналіз поза тренуванням.
Відсутність відео не забороняє завершення заняття: technique = unreviewed.

Результат одного аналізу не є всією обіцяною функцією Plus. Повний шлях
включає подальше ведення програми. Plus може мати автоматизацію лише після
допусків; на Pro/Pro+ рішення залишається за тренером.

## Найпростіший достатній стек

| Частина | Початкове рішення | Коли переглядати |
|---|---|---|
| Web | Чинні FastAPI/Pydantic, SQLAlchemy/Alembic, Jinja/HTML/CSS/vanilla JS | Не переписувати на Next/React для цієї задачі |
| Files | Приватний Supabase Storage; signed TUS, immutable object keys | Інший S3 adapter лише за реальною потребою |
| Video | FFmpeg/ffprobe, OpenCV за потреби | Профілювання перед додатковими бібліотеками |
| Pose | MediaPipe як перший кандидат | RTMPose/MMPose/ONNX лише якщо baseline не проходить перевірку стійки |
| Metrics | Невеликі Python-функції, NumPy за потреби | Нова метрика потребує методики та окремої валідації |
| Knowledge | PostgreSQL: published versions, exercise/criterion tags, bounded text search | pgvector/embeddings лише за виміряно недостатньої якості SQL retrieval |
| LLM | Один провайдер через вузький adapter, Pydantic і domain validation | Вибір model/version/budget за S14-00 та G_AI_QUALITY |
| Jobs | Durable PostgreSQL jobs, окремий worker того самого застосунку | Redis/Celery або GPU лише після виміряної потреби |
| UI | Поточна оболонка, video + Canvas/SVG overlay | Без нового frontend framework |

LlamaIndex/Haystack розглянуті, але для вузького першого pipeline достатньо
власних retrieval → prompt → validated response функцій. MLflow, DVC,
fine-tuning, мікросервіси та універсальні repository/service ієрархії
не входять у початковий обсяг. Фіксуємо model/config/hash і evaluation results.
Новий Python/CV пакет не імпортується при старті web, якщо AI вимкнено.
Сумісність із Python 3.13 і цільовим worker OS перевіряє S14-00;
існуючий toolchain не знижуємо мовчки заради бібліотеки.

## Досліджені джерела та межі доказів

Офіційні джерела прочитані 2026-11-24 через Firecrawl MCP. CLI у цій
сесії повертав DNS error; MCP search/scrape працювали. Це перевірка
документації, **не benchmark**, не інсталяція моделей і не provider release.

| Джерело | Що підтверджує / як використовуємо |
|---|---|
| [MediaPipe Pose](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker) | 33 landmarks, image/world coordinates, visibility/presence; відсутні потрібні анатомічні точки не вигадуємо |
| [MediaPipe Python](https://ai.google.dev/edge/mediapipe/solutions/setup_python) | Перевіряти підтримку конкретних Python/OS/wheels; документ не замінює фактичний install/run |
| [MMPose deployment](https://mmpose.readthedocs.io/en/latest/user_guides/how_to_deploy.html) | Шлях експорту RTMPose до ONNX; запасний кандидат |
| [MMPose license](https://github.com/open-mmlab/mmpose/blob/main/LICENSE) | Apache-2.0 для коду; права на конкретні weights і datasets перевіряються окремо |
| [FFmpeg legal](https://ffmpeg.org/legal.html) | Ліцензійні умови залежать від збірки й enabled components; фіксуємо фактичну збірку |
| [Storage private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals) | Приватний bucket та контроль доступу; signed URL дає доступ до закінчення строку |
| [Resumable upload](https://supabase.com/docs/guides/storage/uploads/resumable-uploads) | TUS і signed upload; не вмикати upsert для immutable evidence |
| [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) | Структурована відповідь і refusal handling; кандидат, не вибраний production provider |
| [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output) | Інший кандидат із JSON Schema; не підключати два провайдери наперед |
| [LlamaIndex](https://docs.llamaindex.ai/en/stable/), [Haystack](https://docs.haystack.deepset.ai/docs/intro) | Можливості RAG-фреймворків; поки відкладаємо |
| [pgvector](https://github.com/pgvector/pgvector) | Exact/approximate retrieval; для майбутнього виміряного розширення, не вимога MVP |
| [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) | Можливий локальний multilingual embedding; відкладено разом із vectors |

S14-00 зберігає dataset/model licenses, hashes, split за людьми/кліпами,
ручну розмітку, measured error, latency, RAM, cost і невдалі сценарії.
Held-out набір не використовується для підбору правил чи моделі.
Пороги прийнятності задаються до оцінювання з фаховою перевіркою, а не
підбираються після результату. Немає дозволеного набору/бюджету/методики —
відповідна частина env_blocked. Це не блокує незалежні готові картки.

## Дані та довіра

PostgreSQL є джерелом власника, зв’язків, фактичних результатів і дозволів.
LLM не має DB credentials, SQL tools або права змінювати program tables.

| PostgreSQL | Private object storage |
|---|---|
| Submission/version, upload intents, owner/session_exercise/selected set refs | Original і normalized video |
| Jobs, lease/generation, status, error code, limits | Стиснутий versioned PoseSequence |
| Typed metric rows: criterion, value, unit, interval, quality, method version | Допоміжні thumbnails/тимчасові файли з lifecycle |
| Observations, hypotheses, recommendations, report/proposal versions | Дозволені evaluation datasets поза Git |
| Sources/chunks, publication/license/evidence class, exercise/criterion links | Великі model artifacts за перевіреними правами |
| Manifest: object ref, checksum, original→normalized→pose lineage | Без публічних URL клієнтських відео |

Не створюємо SQL-рядок на кожен кадр. Manifest фіксує timestamps,
coordinate convention, units, dimensions/rotation/crop transforms,
model/config/preprocessing/metric/method/prompt/source versions.
Checksum підтверджує цілісність, але не авторизацію.

Два незалежні входи AI:

1. Серверний SQL read вибирає мінімальні **власні** факти користувача:
   цілі/обмеження, потрібні вимірювання та релевантну історію.
2. Knowledge retrieval вибирає **опубліковані спільні** знання й доступні
   exercise versions. Особисті факти/private notes не індексуються тут.

Початковий LLM input — структуровані факти + затверджені фрагменти,
без raw video або кадрів. Це все одно processing персональних даних:
G_PRIVACY і дозвіл персоналізації потрібні перед реальними викликами.
Навчання моделі має окремий дозвіл і default off.
У prompts/logs не передавати необов’язкові ідентифікатори чи секрети.
Тексти джерел — недовірені дані, а не instructions/tools.

## Внутрішні й HTTP-контракти (заплановані)

| Межа | Вхід → вихід | Власник |
|---|---|---|
| MediaAccessAdapter | Дозволена media version → scoped доступ/відмова | media, S14-02 |
| Upload | Actor + session_exercise → UploadIntent → ValidatedMediaAsset | media, S10-10/11 |
| PoseAdapter | Asset + pinned config → PoseSequence | analysis/CV, S14-11/12 |
| Quality | PoseSequence + MethodVersion → intervals/observability/reasons | analysis/CV, S14-13 |
| Biomechanics | Pose + quality + method → MetricResult[] | analysis, S14-14 |
| Knowledge | Exercise/criteria/locale → bounded KnowledgeContext | knowledge, S14-15/16 |
| Coach | Metrics + minimal own context + knowledge → validated explanation | analysis, S14-17 |
| Recommendations | Explanation + approved catalog/rules → Recommendation[] | analysis, S14-18 |
| Adaptation | Recommendations + current revisions → чинний proposal/preview | planning/analysis, S14-06/21 |

HTTP доповнення:

- `POST /api/session-exercises/{id}/video/uploads` — обмежений upload intent.
- `POST /api/media/uploads/{id}/complete` — перевірка й finalize, не довіра MIME/body.
- Чинний `POST /api/session-exercises/{id}/video` зберігає URL payload;
  додається mutually exclusive `upload_id` і optional `captured_set_log_id`.
- `POST /api/session-exercises/{id}/analyses` — start за exact evidence version
  з idempotency; `GET /api/analyses/{id}` — own status/result.
- Порівняння — owner-scoped projection у progress, без другого журналу фактів.

Усі writes проходять чинні session/CSRF/Origin/ownership/entitlement guards,
вхідні revisions та idempotency policy. Приватні read — no-store.
Artifact URL видається лише після server authorization; жодних довільних
URL для downloader чи ключів Storage у browser. Signed capability має
обмежений scope/строк. Web DB role не отримує BYPASSRLS чи нових owner прав.
Storage credentials не є загальним DB connection для product queries.

## Наукові межі

Кут у проєкції, положення сегментів і коливання — вимірювання;
можлива компенсація — інтерпретація; рухливість/слабкість — гіпотеза,
доки належний тест не надає додаткових даних. Citation не підтверджує
конкретну причину саме в цієї людини.

MediaPipe world coordinates не є валідованим вимірюванням анатомії.
Не заявляємо прямий вимір поперекової кривизни, ребер чи лопаток за
звичайними sparse landmarks, не діагностуємо травми. Shoulder/elbow/hip/
knee/ankle/body line і temporal stability доступні лише в межах
перевіреної методики та видимості; frontal symmetry не виводиться зі
стійки строго збоку. Missing point — не нуль. Confidence detector,
якість вимірювання та обґрунтованість пояснення — різні поля.

Для припущення про рухливість/контроль система може рекомендувати
затверджений assessment із S12. S12 використовує звичайні sessions;
звичайне відео вправи не перетворюється на обов’язкову assessment-програму.
Жодних вигаданих реабілітаційних призначень чи нормативів. Симптоми/травма
не є підставою для автоматичного експерименту з навантаженням.

## М’яке впровадження й надійність

Default off; спочатку дозволений benchmark, потім shadow, report,
proposal і лише після допусків обмежений auto. Shadow/report теж
потребують дозволів processing і належної перевірки якості.
S14-22 описує фінальний mode controller; до нього кожний модуль має
fail-closed readiness, тому рання картка не робить реальний API доступним.
Стан code_done/local_verified не означає external_verified/approved_for_sale.

Перший інтерфейс використовує native file/camera capture з fallback
вибором файлу; окремий recorder/editor не потрібен. Обробка фонова,
progress показує відомі stages, а не вигаданий відсоток.
Помилка upload/AI не стирає set logs і не заважає завершити вправу без відео.

Одна команда — одна транзакція; network/decode/inference не тримають
довгі DB locks. SQL і object storage не мають спільного commit:
durable intent/state, checksum verification, retry/reconcile та orphan cleanup.
Ліміти size/duration/frame count/dimensions/time/RAM/concurrency/cost
затверджуються до реальних upload; повтори bounded, помилки спостережувані
без приватних payloads. Decoder не відкриває довільні мережеві джерела.

Delete/revoke збільшує generation, зупиняє нове читання/send/publish.
Worker перевіряє lease/generation перед публікацією; пізній результат
не відновлює видалені файли. Очищення охоплює originals, normalized,
poses, thumbnails, temp та abandoned uploads. Уже відправлений зовнішній
запит неможливо гарантовано скасувати; результат відхиляється.
У signed URL є залишкове вікно до expiry; не обіцяти миттєве відкликання.
Retention строків, reports і backups — G_PRIVACY, не мовчазне «назавжди».

Порівнюються тільки сумісні method/metric/pose/preprocess versions,
ракурси/сторони/одиниці/нормалізації. Для іншої версії показати обмеження
або явно повторно обробити дозволений файл; старі результати зберегти.
Apply перевіряє current owner/entitlement/permissions/rules/revisions
і впливає лише на майбутнє. Pro рішення не видаються за coach-approved
через сам факт відповіді AI.

## Картки, документи та навчання

| Етап | Картки | Що можна перевірити |
|---|---|---|
| 0 | S14-00 | Кандидати, права, actual evaluation, обмеження й витрати |
| 1 | Чинні S06–S09 + S06-07 | Версійний приклад → власна програма → session/set logs без AI |
| 2 | S10-10–S10-14 | Upload → validate → bind → C3 → lifecycle |
| 3 | S14-10–S14-14 | Методика → pose → quality → явні метрики |
| 4 | S14-15–S14-18 | Затверджені знання → SQL retrieval → пояснення → каталог рекомендацій |
| 5 | S14-19–S14-20 | Звіт, skeleton overlay й порівняння |
| 6 | S14-21 + S14-06/08 | Пропозиція через чинний planning command layer |
| 7 | S14-22 + S17-02/03 | Поступовий допуск і реальна перевірка, не автоматичний release |

DAG у `roadmap/tasks.json`; індекс — [ROADMAP](../roadmap/ROADMAP.md).
Нові dependencies додаються лише до невиконаних задач. Старі номери
майбутніх SQL-міграцій є орієнтирами: інтегратор виділяє наступну
реальну Alembic revision; застосовані міграції не переписуються.
Новий SQL не створюється наперед. Hosted migrations/deploy/live charges
цим планом не дозволені.

Дослідження методики, дозволені fixtures, knowledge і перевірки геометрії
можна готувати незалежно. Одна активна картка/writer за чинним validator;
агент-рев’юер read-only. Немає 11 одночасно запущених агентів: ролі
Architect/Product/Frontend/Backend/CV/Biomechanics/Knowledge/AI/DB+Infra/
QA/Security описують відповідальність, не обов’язкову інфраструктуру команди.
Shared migrations/state редагує інтегратор. QA/reviewer не оцінює власну реалізацію.

Цей документ об’єднує product/MVP/architecture/video/pose/biomechanics/
knowledge/AI/data/privacy/test intent без двадцяти дубльованих джерел істини.
Під час відповідної картки конкретні схеми/API/виміряні рішення додаються
до спільних contracts і verification, а не лишаються тільки в чаті.

Навчання власника — Python з основ, одне невелике завдання за раз.
[Правила навчання](learning/README.md), [перша вправа](learning/01-duration.md).
Це synthetic sandbox, не production authorization; код користувача
проходить review/tests перед інтеграцією. Не перезаписувати його ділянку.

## Критерій готовності та відкриті gates

End-to-end: власна програма → приклад → recorded set → private video →
валідні метрики/пояснення → перевірені рекомендації → майбутня адаптація →
наступний запис і чесне порівняння. Старі auth/profile/billing/training
перевірки залишаються зеленими; failures не створюють fake progress.

Не визначено без реальної перевірки: model winner/version, числові quality
thresholds, допустимий clip/resource budget, retention/deletion строків,
вартість/LLM account і production target. Власники рішень і межі —
[owner-gates](owner-gates.md): G_METHOD/G_RULES/G_VIDEO/G_PRIVACY/G_AI_QUALITY.
Вони блокують відповідні real-data/release дії, а не незалежний локальний код.
G_COMMERCE/G_PRODUCTION не відкриваються від завершення документації.
