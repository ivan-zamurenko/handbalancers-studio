"""Questionnaire (self-report). API and DB enforce the same rules; no assessment is derived."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from studio.accounts.service import RevisionConflict, WebTransaction
from studio.shared.context import Actor

Goal = Literal["handstand", "strength", "mobility", "fitness"]
Weekday = Annotated[int, Field(ge=1, le=7, strict=True)]  # ISO: 1 = Monday … 7 = Sunday


def _distinct[T](values: list[T]) -> list[T]:
    if len(set(values)) != len(values):
        raise ValueError("Duplicate values")
    return values


class OnboardingChoices(BaseModel):
    """Non-sensitive guest answers; never identity, entitlement or a row revision."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    goal_codes: Annotated[list[Goal], Field(min_length=1, max_length=4), AfterValidator(_distinct)]
    self_reported_level: Annotated[int, Field(ge=1, le=3, strict=True)]
    session_minutes: Literal[30, 45, 60, 90]
    weekdays: Annotated[list[Weekday], Field(min_length=1, max_length=3), AfterValidator(_distinct)]
    time_of_day: Literal["morning", "afternoon", "evening"] | None = None


class OnboardingInput(OnboardingChoices):
    birth_year: Annotated[int, Field(ge=1920, le=2020)] | None = None
    height_cm: Annotated[int, Field(ge=100, le=250)] | None = None
    weight_kg: Annotated[Decimal, Field(ge=25, le=300, max_digits=4, decimal_places=1)] | None = (
        None
    )
    expected_revision: int = Field(ge=0, le=2_147_483_647)


FIELDS = (
    "goal_codes",
    "self_reported_level",
    "session_minutes",
    "weekdays",
    "time_of_day",
    "birth_year",
    "height_cm",
    "weight_kg",
)


def _read(session: Session) -> dict[str, object] | None:
    row = (
        session.execute(
            text(f"SELECT {', '.join(FIELDS)}, row_version FROM studio.onboarding_profiles")
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    data = {name: row[name] for name in FIELDS}
    data["weight_kg"] = float(row["weight_kg"]) if row["weight_kg"] is not None else None
    data["revision"] = row["row_version"]
    if data["birth_year"]:
        # Birth year only (less sensitive than a date): age is approximate by design.
        data["age"] = datetime.now(UTC).year - int(str(data["birth_year"]))
    return data


def get_onboarding(transaction: WebTransaction, actor: Actor) -> dict[str, object] | None:
    with transaction(actor) as session:
        return _read(session)


def save_onboarding(
    transaction: WebTransaction, actor: Actor, data: OnboardingInput
) -> dict[str, object]:
    values = data.model_dump(include=set(FIELDS))
    with transaction(actor) as session:
        if data.expected_revision == 0:
            columns = ", ".join(FIELDS)
            placeholders = ", ".join(f":{name}" for name in FIELDS)
            changed = session.execute(
                text(
                    f"INSERT INTO studio.onboarding_profiles (user_id, {columns}) "
                    f"VALUES (:user_id, {placeholders}) "
                    "ON CONFLICT (user_id) DO NOTHING RETURNING row_version"
                ),
                {"user_id": actor.user_id, **values},
            ).scalar_one_or_none()
        else:
            assignments = ", ".join(f"{name} = :{name}" for name in FIELDS)
            changed = session.execute(
                text(
                    f"UPDATE studio.onboarding_profiles SET {assignments}, updated_at = now(), "
                    "row_version = row_version + 1 WHERE row_version = :expected "
                    "RETURNING row_version"
                ),
                {"expected": data.expected_revision, **values},
            ).scalar_one_or_none()
        current = _read(session)
    if changed is None:
        raise RevisionConflict(current or {})
    assert current is not None
    return current


def setup_required(transaction: WebTransaction, actor: Actor) -> bool:
    with transaction(actor) as session:
        row = session.execute(
            text(
                "SELECT u.first_name IS NOT NULL AND u.last_name IS NOT NULL AS named, "
                "EXISTS (SELECT 1 FROM studio.onboarding_profiles) AS answered "
                "FROM studio.users u"
            )
        ).one()
    return not (row.named and row.answered)
