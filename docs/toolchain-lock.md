# Toolchain S00-02

Перевірено 2026-10-06 на macOS arm64. Версії обрано для нової реалізації;
старі manifests не використовувалися.

| Інструмент | Зафіксована версія | Джерело фіксації |
|---|---|---|
| Python | 3.13.3 | `.python-version`; пакет підтримує Python 3.13 |
| uv | 0.12.23 | `tool.uv.required-version` |
| uv build backend | 0.12.23 | `build-system.requires` |
| Node | 24.21.0 | `.node-version`, `package.json` engines |
| npm | 11.19.0 | `package.json` engines / packageManager |
| pytest | 9.1.1 | `pyproject.toml`, `uv.lock` |
| Ruff | 0.16.10 | `pyproject.toml`, `uv.lock` |

Node отримано з офіційного nodejs.org. SHA256 архіву
`node-v24.21.0-darwin-arm64.tar.gz` звірено з офіційним `SHASUMS256.txt`:
`bed7eea5325e1108f32ce5228ddd6a5f0f08a499ee42aa7442aea583702f6057`.
uv та Python dev-пакети отримано з PyPI. Транзитивні версії й хеші — в `uv.lock`.
Build backend зафіксовано окремо, оскільки build requirements не є runtime-залежностями.

## Встановлення

Потрібні зазначені Python, Node/npm та uv у PATH. Для цієї робочої машини
uv і Node встановлено лише в ігноровану `.local-tools/`; системний Node не змінено:

```sh
export PATH="$PWD/.local-tools/node/bin:$PWD/.local-tools/uv-env/bin:$PATH"
export UV_CACHE_DIR="$PWD/.local-tools/uv-cache"
export npm_config_cache="$PWD/.local-tools/npm-cache"
uv sync --locked
npm ci
python3 -m unittest discover -s tools/tests -v
```

Ці локальні шляхи не входять до Git. У новому checkout спочатку встановіть
версії з таблиці своїм менеджером інструментів. Потім достатньо `uv sync --locked`
і `npm ci`. `.npmrc` відхиляє несумісні Node/npm через `engine-strict`.

`studio` встановлюється editable із `server/studio`. Тести імпортують його
з іншого каталогу в ізольованому Python (`-I`) та перевіряють editable metadata.
Інший тест двічі встановлює Python/npm залежності в тимчасовій копії
й порівнює байти обох lock-файлів. Перший цикл починається з чистого середовища.

## Доповнення S00-03

Додано FastAPI 0.142.2 і Uvicorn 0.54.0 як runtime-залежності,
HTTPX 0.28.1 як test dependency. Точні транзитивні версії — в uv.lock.
Інсталяцію й контракти перевірено на Python 3.13.3.

Starlette 1.7.0 попереджає, що його TestClient у майбутньому вимагатиме
httpx2 замість httpx. Поточний pinned набір сумісний, тести проходять;
warning не приховується. Перехід на інший HTTP-клієнт не входить у S00-03.

## Поточна межа

Є фабрика FastAPI, `/health/live` та типізовані Settings. npm dev-залежності поки порожні,
JS harness ще не реалізовано. Інші бібліотеки додаються разом із першою
задачею, що їх використовує. Playwright/axe
та JS harness — наступні відповідні картки. Порожній npm lock фіксує початковий
стан tooling і дозволяє `npm ci`, але не свідчить про готові browser-тести.
Версію PostgreSQL потрібно обрати при створенні реального локального стенда.

## Джерела

- [uv: locked sync та editable install](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uv build backend: module-root / module-name](https://docs.astral.sh/uv/concepts/build-backend/)
- [Node 24.21.0 release та контрольні суми](https://nodejs.org/dist/v24.21.0/)

- [FastAPI: TestClient](https://fastapi.tiangolo.com/tutorial/testing/)
- [Uvicorn: application factory](https://www.uvicorn.org/settings/)

## Доповнення S00-04

Pydantic 2.13.5, уже наявний у lock, оголошено прямою залежністю Settings.
Жодних транзитивних версій не оновлено. Environment loader явно читає тільки
задекларовані імена; BaseModel не читає environment або dotenv неявно.
Це дозволяє передавати ізольовані test settings без доступу до секретів машини.
Налаштування незмінні, секретні поля — SecretStr. Помилки валідації перебудовуються
без початкових даних і контексту, включно з некоректним JSON. Повідомлення
навмисно загальне: перевірити APP_ENV, PUBLIC_ORIGIN та поля секретів.

- [Pydantic: wrap validators](https://pydantic.dev/docs/validation/latest/concepts/validators/)
