# Frontend: компоненты и страницы

## Общий слой
Jinja base shell + macros, ES modules и CSS variables. Семантические компоненты: FormField, ErrorSummary, PrimaryButton, Dialog, SaveStatus, ThemeSwitch, LanguageSwitch, Pagination, EmptyState. Это шаблоны/контроллеры, не новый React/framework runtime. Каждый компонент имеет loading/empty/error/disabled/focus/success при наличии соответствующего действия.

## Auth/Public
RegistrationForm, VerificationForm, LoginForm, RecoveryForm, ProfileCompletionForm, OnboardingStepper, PlanSelector, CheckoutStatus. Порядок user journey не зависит от порядка написания кода: цели→пакет→регистрация/вход→Checkout→кабинет. Не навязывать раннюю регистрацию перед выбором целей.

## Клиент C1
TodayCard из реального occurrence/session. CurrentProgramSummary с номером version. WeeklyProgress по фактам. FeedbackSummary только опубликованный. Calendar с replace/add/move preview. ProgramCatalog и общий ProgramBuilder. SessionHistory/detail. Profile/Preferences/Subscription. AssessmentCard ведёт в обычный C3. AnalysisStatus честно отделяет queued/needs_input/published.

## C3
SessionHeader, ExerciseInstructions (свернутые по умолчанию после начала), SetTarget, TypedSetInput, RestTimer, SaveStatus, Pause/Resume, SkipReasonDialog, CompleteSummary. Не закрывать тренировку пока есть неподтверждённые writes. Error/retry сохраняют ввод. Отсутствие видео не блокирует завершение. Theme change не пересоздаёт controller/DOM формы. Next только после сохранения либо явного skip.

## Админка A1
Desktop: ClientList | ClientContext | ReviewPanel. Mobile: выбор панели с сохранением client/draft. Дополнительные страницы: ExerciseEditor, ProgramBuilder, AssignmentPreview, PlanPermissions, RuleSetEditor, ScheduleChangeRequests, AssessmentProtocolEditor, AssessmentReview, AIProposalDetail, ServiceFulfilment (после Pro+ решения). Мобильная админка не является простым stacking всех трёх колонок.

## Routes UI
Public: /, /onboarding, /plans, /register, /verify-email, /login, /recovery, /checkout/status.
Member: /dashboard, /programs, /programs/:id, /programs/:id/edit, /calendar, /workouts/:sessionId, /history, /history/:id, /feedback, /assessments, /profile, /subscription.
Coach: /coach, /coach/clients/:id, /coach/exercises, /coach/exercises/:id/edit, /coach/programs, /coach/programs/:id/edit, /coach/assignments/new, /coach/reviews/:id, /coach/rules, /coach/change-requests, /coach/assessments, /coach/services.

Endpoint permissions на сервере; скрытая кнопка не защита. Paths — baseline v4, не описание существующего backend.

## Темы и локализация
Смысловые CSS tokens из references. Никаких font binaries в репозитории. auto использует local device clock, а не геолокацию/сервер. Client и coach preferences независимы. Account preference синхронизируется с сервером, локальная user-scoped копия нужна только как быстрый boot fallback. До установления authenticated profile нельзя показать предыдущие account preferences как собственные данные нового клиента.

Визуальная проверка: C1/A1/C3 × light/dark × 390/1440. Состояния ошибок/conflicts + длинный UA/EN copy. Скриншоты не единственный accessibility тест. Реальные формы не обязаны пиксель-в-пиксель повторять размер synthetic текста, но сохраняют утверждённую композицию/иерархию.
