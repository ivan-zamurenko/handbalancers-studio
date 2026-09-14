"""The onboarding contract is strict and versioned independently from presentation."""

from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

Goal = Literal["handstand", "strength", "mobility", "fitness"]
PlanId = Literal["essential", "plus", "pro", "pro_plus"]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True)


class OnboardingInput(StrictBody):
    goals: list[Goal] = Field(min_length=1, max_length=4)
    experience: Literal["beginner", "intermediate", "advanced"]
    days: list[Annotated[StrictInt, Field(ge=0, le=6)]] = Field(min_length=1, max_length=3)
    minutes: Literal[30, 45, 60, 90]
    minutes_plus: StrictBool = False
    timezone: str = Field(min_length=1, max_length=64)
    locale: Literal["uk", "en"] = "uk"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone") from None
        return value

    @model_validator(mode="after")
    def coherent_answers(self):
        if self.minutes_plus and self.minutes != 60:
            raise ValueError("minutes_plus is available only with 60 minutes")
        for field in (self.goals, self.days):
            if len(field) != len(set(field)):
                raise ValueError("Selections cannot contain duplicates")
        self.days = sorted(self.days)
        return self


def onboarding_view(answers: dict | None) -> dict | None:
    """Expose legacy JSON without rewriting a user's historical availability.

    Old short sessions or weeks with more than three days remain accurate on the
    dashboard. Editing them requires choosing one of the current input options.
    """
    if answers is None:
        return None
    result = {key: value for key, value in answers.items() if key in OnboardingInput.model_fields}
    result.setdefault("minutes_plus", False)
    return result


class PreviewRegistration(StrictBody):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def plain_name(cls, value):
        if any(ord(char) < 32 or char in "<>" for char in value):
            raise ValueError("Use a plain display name")
        return value


class CheckoutInput(StrictBody):
    plan_id: PlanId


class ProfileInput(StrictBody):
    first_name: str = Field(min_length=1, max_length=48)
    last_name: str = Field(min_length=1, max_length=48)

    @field_validator("first_name", "last_name")
    @classmethod
    def plain_person_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Use a plain name")
        if any(ord(char) < 32 or char in "<>" for char in value):
            raise ValueError("Use a plain name")
        return value


class EmailLogin(StrictBody):
    # Passwords must never be trimmed or included in repr/validation responses.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, hide_input_in_errors=True)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128, repr=False)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value):
        import re

        value = value.strip().lower()
        if not re.fullmatch(
            r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value
        ):
            raise ValueError("Use a valid email address")
        return value


class EmailRegistration(EmailLogin, ProfileInput):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, hide_input_in_errors=True)


class VerificationInput(StrictBody):
    code: str = Field(pattern=r"^[0-9]{6}$", repr=False)
