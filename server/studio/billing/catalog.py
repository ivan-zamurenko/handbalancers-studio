"""Product capability matrix, independent of identity, payment SDKs and UI."""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Plan:
    capabilities: frozenset[str]
    trial_allowed: bool = False


_SELF = frozenset({"published_catalog", "training_write", "program_builder"})
_AI = _SELF | {"ai_guidance"}
_COACH = _AI | {"weekly_human_review"}

PLANS = MappingProxyType(
    {
        "essential": Plan(_SELF, trial_allowed=True),
        "plus": Plan(_AI, trial_allowed=True),
        "pro": Plan(_COACH),
        "pro-plus": Plan(_COACH | {"personal_chat", "coaching_calls"}),
    }
)
