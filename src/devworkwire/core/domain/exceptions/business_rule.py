from typing import Optional

from .base import DomainException


class BusinessRuleViolationException(DomainException):
    """
    Raised when a domain business rule is violated.

    Attributes:
        rule: The business rule that was violated
        entity_key: The key of the entity involved (if applicable)
        details: Additional context about the violation
    """

    def __init__(
        self,
        rule: str,
        entity_key: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.rule = rule
        self.entity_key = entity_key
        self.details = details

        message = f"Business rule violation: {rule}"
        if entity_key:
            message += f" for {entity_key}"
        if details:
            message += f" - {details}"

        super().__init__(message)
