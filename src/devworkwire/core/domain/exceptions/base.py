class DomainException(Exception):
    """
    Base exception for all domain-related errors.

    All custom domain exceptions should inherit from this class
    to distinguish domain errors from infrastructure or system errors.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
