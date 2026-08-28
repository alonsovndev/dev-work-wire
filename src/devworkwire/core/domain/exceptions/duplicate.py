from .base import DomainException


class DuplicateEntityException(DomainException):
    """
    Raised when attempting to create an entity that already exists.

    Attributes:
        entity_type: The type of entity (e.g., "Epic", "UserStory")
        identifier: The key or ID of the duplicate entity
    """

    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"Duplicate {entity_type} already exists: {identifier}")
