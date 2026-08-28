from dataclasses import dataclass
from enum import Enum


class PriorityLevel(int, Enum):
    """Priority levels ordered from highest to lowest."""

    HIGHEST = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


@dataclass(frozen=True)
class Priority:
    """
    Value object representing issue priority.

    Immutable - the priority level of an issue should not change once assigned.
    """

    name: str
    level: PriorityLevel

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Priority):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def is_higher_than(self, other: "Priority") -> bool:
        return self.level < other.level

    def is_lower_than(self, other: "Priority") -> bool:
        return self.level > other.level

    # Common priority instances
    @classmethod
    def highest(cls) -> "Priority":
        return cls(name="Highest", level=PriorityLevel.HIGHEST)

    @classmethod
    def high(cls) -> "Priority":
        return cls(name="High", level=PriorityLevel.HIGH)

    @classmethod
    def medium(cls) -> "Priority":
        return cls(name="Medium", level=PriorityLevel.MEDIUM)

    @classmethod
    def low(cls) -> "Priority":
        return cls(name="Low", level=PriorityLevel.LOW)

    @classmethod
    def lowest(cls) -> "Priority":
        return cls(name="Lowest", level=PriorityLevel.LOWEST)

    @classmethod
    def from_jira_name(cls, name: str) -> "Priority":
        """Creates Priority from Jira's priority name."""
        name_lower = name.lower()
        if name_lower in ("highest", "blocker", "critical"):
            return cls.highest()
        elif name_lower in ("high", "major"):
            return cls.high()
        elif name_lower in ("medium", "average", "normal"):
            return cls.medium()
        elif name_lower in ("low", "minor"):
            return cls.low()
        elif name_lower in ("lowest",):
            return cls.lowest()
        return cls(name=name, level=PriorityLevel.MEDIUM)
