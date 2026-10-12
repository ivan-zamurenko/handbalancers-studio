"""Public auth inputs. Passwords are never normalized or echoed."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    ),
]


class SignupInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    first_name: Name
    last_name: Name
    email: Email
    password: SecretStr = Field(repr=False)

    @field_validator("password")
    @classmethod
    def password_length(cls, value: SecretStr) -> SecretStr:
        if not 8 <= len(value.get_secret_value()) <= 256:
            raise ValueError("Invalid password length")
        return value
