import re
from dataclasses import dataclass

from devworkwire.core.domain.exceptions import BusinessRuleViolationException

# Jira issue keys look like '<PROJECT_KEY>-<NUMBER>', e.g. 'PROJ-123'.
_ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


@dataclass(frozen=True)
class IssueId:
    """
    Value object representing a Jira issue identifier.

    Immutable by design - the identifier of an issue should not change.
    """

    key: str
    numeric_id: int

    def __post_init__(self):
        if not _ISSUE_KEY_PATTERN.match(self.key):
            raise BusinessRuleViolationException(
                "Invalid Jira issue key",
                details=(
                    f"'{self.key}' does not match '<PROJECT>-<number>' (e.g. PROJ-123)"
                ),
            )

    def __str__(self) -> str:
        return self.key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IssueId):
            return False
        return self.key == other.key and self.numeric_id == other.numeric_id

    def __hash__(self) -> int:
        return hash((self.key, self.numeric_id))

    @classmethod
    def from_string(cls, key: str) -> "IssueId":
        """
        Creates an IssueId from a string like 'PROJ-123'.

        Raises:
            BusinessRuleViolationException: If the key is empty or not a
                valid Jira issue key.
        """
        normalized = (key or "").strip()
        if not _ISSUE_KEY_PATTERN.match(normalized):
            raise BusinessRuleViolationException(
                "Invalid Jira issue key",
                details=(
                    f"'{key}' does not match '<PROJECT>-<number>' (e.g. PROJ-123)"
                ),
            )
        return cls(
            key=normalized,
            numeric_id=int(normalized.rsplit("-", 1)[1]),
        )
