"""Trusted identity supplied by server-side authentication, never request payloads."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Actor:
    """Product user identity; constructing this value does not authenticate a user."""

    user_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("Actor requires a UUID")
