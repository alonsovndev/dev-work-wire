from dataclasses import dataclass
from typing import Optional

from devworkwire.core.domain.exceptions import BusinessRuleViolationException


@dataclass(frozen=True)
class Label:
    """
    Value object representing a Jira label.

    Immutable - labels are simple string identifiers.
    """

    name: str

    def __post_init__(self):
        if not self.name:
            raise BusinessRuleViolationException("Label name cannot be empty")
        if len(self.name) > 255:
            raise BusinessRuleViolationException(
                "Label name cannot exceed 255 characters"
            )

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Label):
            return False
        # Labels are case-insensitive in Jira
        return self.name.lower() == other.name.lower()

    def __hash__(self) -> int:
        return hash(self.name.lower())

    @classmethod
    def from_optional(cls, name: Optional[str]) -> Optional["Label"]:
        """Creates Label from an optional string."""
        if name is None:
            return None
        return cls(name=name)


@dataclass(frozen=True)
class LabelSet:
    """
    Value object representing a collection of labels.

    Immutable - operations return new instances.
    """

    labels: tuple[Label, ...]

    def __post_init__(self):
        if len(self.labels) != len(set(self.labels)):
            raise BusinessRuleViolationException("Duplicate labels are not allowed")

    @classmethod
    def empty(cls) -> "LabelSet":
        return cls(labels=())

    @classmethod
    def from_list(cls, names: list[str]) -> "LabelSet":
        """Creates LabelSet from a list of label names."""
        if not names:
            return cls.empty()

        labels = tuple(Label(name=name) for name in names)
        return cls(labels=labels)

    def __str__(self) -> str:
        return ", ".join(label.name for label in self.labels)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LabelSet):
            return False

        return set(self.labels) == set(other.labels)

    def __hash__(self) -> int:
        return hash(frozenset(self.labels))

    def __len__(self) -> int:
        return len(self.labels)

    def __iter__(self):
        return iter(self.labels)

    def contains(self, label: Label) -> bool:
        return label in self.labels

    def has_label_named(self, name: str) -> bool:
        """Check if set contains a label with given name (case-insensitive)."""
        name_lower = name.lower()
        return any(label.name.lower() == name_lower for label in self.labels)

    def add(self, label: Label) -> "LabelSet":
        """Returns a new LabelSet with the added label."""
        if label in self.labels:
            return self

        return LabelSet(labels=(*self.labels, label))

    def remove(self, label: Label) -> "LabelSet":
        """Returns a new LabelSet with the label removed."""
        return LabelSet(
            labels=tuple(existing for existing in self.labels if existing != label)
        )
