import secrets

import pytest
from pydantic import ValidationError

from studio.plans import public_plans
from studio.schemas import OnboardingInput, PreviewRegistration, onboarding_view
from studio.security import csrf_token, token_hash
from studio.settings import Settings


@pytest.mark.parametrize(
    "change",
    [
        {"primary_goal": "mobility"},
        {"goals": []},
        {"goals": ["strength", "strength"]},
        {"days": []},
        {"days": [0, 1, 2, 3]},
        {"days": [0, 0]},
        {"days": [True]},
        {"days": [7]},
        {"days": ["1"]},
        {"minutes": 75},
        {"minutes": 90, "minutes_plus": True},
        {"minutes": 15},
        {"minutes": 20},
        {"minutes_plus": True},
        {"minutes": 60, "minutes_plus": "true"},
        {"minutes": 60, "minutes_plus": 1},
        {"equipment": ["none", "wall"]},
        {"timezone": "Unknown/Zone"},
        {"locale": "ua"},
        {"experience": "expert"},
        {"user_id": "another-user"},
    ],
)
def test_invalid_onboarding_rejected(answers, change):
    with pytest.raises(ValidationError):
        OnboardingInput(**(answers | change))


def test_onboarding_normalizes_week_order(answers):
    assert OnboardingInput(**(answers | {"days": [6, 0, 2]})).days == [0, 2, 6]


@pytest.mark.parametrize(
    "minutes, minutes_plus", [(30, False), (45, False), (60, False), (60, True), (90, False)]
)
@pytest.mark.parametrize("days", [[0], [1, 3], [0, 2, 6]])
def test_current_time_and_day_choices(answers, minutes, minutes_plus, days):
    parsed = OnboardingInput(
        **(
            answers
            | {
                "minutes": minutes,
                "minutes_plus": minutes_plus,
                "days": days,
            }
        )
    )
    assert parsed.minutes == minutes
    assert parsed.minutes_plus is minutes_plus
    assert parsed.days == days


def test_legacy_view_keeps_availability_without_mutating_source(answers):
    legacy = answers | {
        "primary_goal": "handstand",
        "equipment": ["wall"],
        "days": [0, 1, 2, 4, 6],
        "minutes": 20,
    }
    legacy.pop("minutes_plus")
    result = onboarding_view(legacy)
    assert "primary_goal" not in result and "equipment" not in result
    assert result["minutes_plus"] is False
    assert result["minutes"] == 20 and result["days"] == [0, 1, 2, 4, 6]
    assert "minutes_plus" not in legacy and legacy["primary_goal"] == "handstand"
    assert onboarding_view(None) is None


@pytest.mark.parametrize("name", ["", "  ", "<script>", "a\nname", "a" * 101])
def test_display_name_boundaries(name):
    with pytest.raises(ValidationError):
        PreviewRegistration(name=name)


def test_configuration_fails_closed_and_hides_secrets(settings):
    secret = secrets.token_urlsafe(32)
    common = {
        "_env_file": None,
        "session_secret": secret,
        "database_url": "postgresql+psycopg://localhost/studio_test",
    }
    with pytest.raises(ValidationError):
        Settings(**common, app_env="production", base_url="http://studio.example")
    with pytest.raises(ValidationError):
        Settings(
            **common, app_env="production", base_url="https://studio.example", local_preview=True
        )
    with pytest.raises(ValidationError):
        Settings(**(common | {"database_url": "sqlite:///local.db"}), app_env="test")
    assert settings.session_secret.get_secret_value() not in repr(settings)
    assert settings.database_url.get_secret_value() not in repr(settings)


def test_session_hash_and_csrf_have_separate_purposes(settings):
    a, b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    assert token_hash(a) != a
    assert csrf_token(a, settings) != token_hash(a)
    assert csrf_token(a, settings) != csrf_token(b, settings)


def test_plan_catalogue_has_server_prices():
    assert [(plan["id"], plan["price_cents"]) for plan in public_plans()] == [
        ("essential", 1999),
        ("plus", 4999),
        ("pro", 17999),
        ("pro_plus", 29999),
    ]
    assert all(plan["currency"] == "EUR" for plan in public_plans())
