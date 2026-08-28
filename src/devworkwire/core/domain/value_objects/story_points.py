from dataclasses import dataclass
from typing import Optional

from devworkwire.core.domain.exceptions import BusinessRuleViolationException


@dataclass(frozen=True)
class StoryPoints:
    """
    Value object representing story points for estimation.

    Immutable - story points should not change once assigned.
    Validates that points are non-negative.
    """

    value: int

    def __post_init__(self):
        if self.value < 0:
            raise BusinessRuleViolationException("Story points must be non-negative")

    @classmethod
    def none(cls) -> "StoryPoints":
        """Creates an unset story points value."""
        return cls(value=0)

    @classmethod
    def from_optional(cls, value: Optional[int]) -> Optional["StoryPoints"]:
        """Creates StoryPoints from an optional integer."""
        if value is None:
            return None
        return cls(value=value)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StoryPoints):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __add__(self, other: "StoryPoints") -> "StoryPoints":
        return StoryPoints(value=self.value + other.value)

    def __mul__(self, other: int) -> "StoryPoints":
        return StoryPoints(value=self.value * other)
