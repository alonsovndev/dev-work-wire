from .base import DomainException


class UnauthorizedWorkspaceAccess(DomainException):
    """
    Exception raised when access is attempted on an unauthorized workspace.

    Attributes:
        workspace_key -- workspace key attempted
        allowed_workspaces -- list of allowed workspace keys
    """

    def __init__(self, workspace_key: str, allowed_workspaces: str):
        self.workspace_key = workspace_key
        self.allowed_workspaces = allowed_workspaces
        message = (
            f"Access to workspace '{workspace_key}' is not allowed. "
            f"Allowed workspaces: {allowed_workspaces}."
        )
        super().__init__(message)
