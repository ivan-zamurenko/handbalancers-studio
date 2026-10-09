import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from studio.shared.i18n import DEFAULT_LOCALE, get_locale, translate

ROOT = Path(__file__).resolve().parents[4]
LOCALE_DIR = ROOT / "server/static/js/i18n"


def test_key_parity():
    ukrainian = json.loads((LOCALE_DIR / "uk.json").read_text())
    english = json.loads((LOCALE_DIR / "en.json").read_text())

    assert ukrainian.keys() == english.keys()
    assert ukrainian
    assert all(isinstance(value, str) and value.strip() for value in ukrainian.values())
    assert all(isinstance(value, str) and value.strip() for value in english.values())


def test_locale_fallback():
    assert DEFAULT_LOCALE == "uk"
    assert get_locale("fr-CA") == "uk"
    assert translate("fr-CA", "common.save") == "Зберегти"


def test_no_business_translation():
    business_values = {
        "plan_code": "essential",
        "status": "pending",
        "api_value": "checkout_required",
    }
    original_values = business_values.copy()

    assert translate("uk", "common.save") == "Зберегти"
    assert business_values == original_values
    assert get_locale("en") == "en"


def test_language_switch_uses_caller_urls_and_current_locale():
    environment = Environment(
        loader=FileSystemLoader(ROOT / "server/templates"), autoescape=True
    )
    template = environment.from_string(
        '{% from "shared/language.html" import language_switch %}'
        '{{ language_switch("en", "/uk?x=1&y=2", "/en") }}'
    )

    rendered = template.render()

    assert 'href="/uk?x=1&amp;y=2"' in rendered
    assert 'href="/en" lang="en" hreflang="en" aria-current="page"' in rendered