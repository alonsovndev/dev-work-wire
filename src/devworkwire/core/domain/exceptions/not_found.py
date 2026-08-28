from .base import DomainException


class EntityNotFoundException(DomainException):
    """
    Raised when an entity cannot be found in the repository.

    Attributes:
        entity_type: The type of entity that was not found (e.g., "Epic", "UserStory")
        identifier: The key or ID used to look up the entity
    """

    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} not found: {identifier}")
