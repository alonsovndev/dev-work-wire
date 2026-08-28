from typing import Optional

from .base import DomainException


class InvalidStatusTransitionException(DomainException):
    """
    Raised when an entity is moved to an invalid status.

    Attributes:
        entity_key: The key of the entity
        current_status: The current status
        target_status: The status that was requested
        valid_transitions: List of valid target statuses from current status
    """

    def __init__(
        self,
        entity_key: str,
        current_status: str,
        target_status: str,
        valid_transitions: Optional[list[str]] = None,
    ):
        self.entity_key = entity_key
        self.current_status = current_status
        self.target_status = target_status
        self.valid_transitions = valid_transitions or []

        message = (
            f"Invalid status transition for {entity_key}: "
            f"'{current_status}' -> '{target_status}'"
        )
        if self.valid_transitions:
            message += f". Valid transitions: {', '.join(self.valid_transitions)}"

        super().__init__(message)
