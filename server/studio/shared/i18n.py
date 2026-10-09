import json
from functools import lru_cache
from pathlib import Path
from typing import Final

DEFAULT_LOCALE: Final = "uk"
SUPPORTED_LOCALES: Final = frozenset({"uk", "en"})
_CATALOG_DIR = Path(__file__).resolve().parents[2] / "static" / "js" / "i18n"


def get_locale(locale: str | None) -> str:
    candidate = (locale or DEFAULT_LOCALE).strip().replace("_", "-").lower().split("-", 1)[0]
    return candidate if candidate in SUPPORTED_LOCALES else DEFAULT_LOCALE


@lru_cache(maxsize=len(SUPPORTED_LOCALES))
def _load_catalog(locale: str) -> dict[str, str]:
    path = _CATALOG_DIR / f"{locale}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def translate(locale: str | None, key: str) -> str:
    resolved_locale = get_locale(locale)
    catalog = _load_catalog(resolved_locale)
    return catalog.get(key, key)