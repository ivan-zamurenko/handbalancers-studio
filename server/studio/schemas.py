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
    minutes: Literal[30, 45, 60]
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
