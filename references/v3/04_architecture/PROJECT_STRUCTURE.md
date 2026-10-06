# Предлагаемая структура проекта

```text
server/
  studio/
    main.py
    settings.py
    db.py
    auth/
    accounts/
    catalog/
    programs/
    planning/
      service.py
      compatibility.py
      permissions.py
      previews.py
      schemas.py
      routes.py
    training/
    reviews/
    assessments/
    media/
      adapters/
    analysis/
    billing/
    progress/
    shared/
      authorization.py
      idempotency.py
      audit.py
      errors.py
    jobs/
  templates/
    public/
    member/
    coach/
    shared/
  static/
    css/
      tokens.css
      components.css
      member.css
      coach.css
    js/
      api/
      state/
      features/member/
      features/coach/
      components/
      i18n/
  alembic/versions/
  tests/
    unit/
    integration/
    security/
    contracts/
scripts/
docs/
compose.yaml
```

Это целевая организация, не описание файлов уже проверенного репозитория. В каталоге создаются только необходимые файлы; не копировать одинаковые services/repositories «для симметрии».
Доменные команды общие. UI member/coach различается разрешениями и представлением, а не алгоритмом подсчёта.
Файлы `07_design/preview/assets/selected-preview.js` — код демонстрации, не готовый production state layer.
Секретное окружение и БД не включать в репозиторий или handoff.
