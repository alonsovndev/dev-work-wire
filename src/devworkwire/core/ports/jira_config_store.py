import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from devworkwire.core.domain.exceptions import BusinessRuleViolation

PROJECT_KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
_LOCAL_HOSTS = ("localhost", "127.0.0.1")


def normalize_project_key(project_key: str) -> str:
    key = project_key.strip().upper()
    if not PROJECT_KEY_RE.fullmatch(key):
        raise BusinessRuleViolation(
            "Jira project key must start with a letter and contain only letters, digits or '_'"
        )
    return key


@dataclass(frozen=True)
class JiraCredentials:
    base_url: str
    email: str
    api_token: str

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        email = self.email.strip()
        api_token = self.api_token.strip()
        if not all((base_url, email, api_token)):
            raise BusinessRuleViolation("Jira base URL, email and API token are all required")
        parsed = urlparse(base_url)
        is_local_http = parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS
        if not parsed.hostname or not (parsed.scheme == "https" or is_local_http):
            raise BusinessRuleViolation(
                "Jira base URL must be an https:// URL (e.g. https://your-domain.atlassian.net)"
            )
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "email", email)
        object.__setattr__(self, "api_token", api_token)


@dataclass(frozen=True)
class JiraProject:
    key: str
    is_default: bool


class JiraConfigStore(ABC):
    """User-level Jira connection plus the list of projects the user works in."""

    @abstractmethod
    def load_credentials(self) -> Optional[JiraCredentials]:
        """Return the stored connection, or None when nothing is stored."""

    @abstractmethod
    def save_credentials(self, credentials: JiraCredentials) -> None:
        """Replace the stored connection; projects are untouched."""

    @abstractmethod
    def list_projects(self) -> list[JiraProject]:
        """Projects in the order they were added; at most one is the default."""

    @abstractmethod
    def add_project(self, project_key: str, make_default: bool = False) -> None:
        """Add a project (no-op if present). The first project becomes the default."""

    @abstractmethod
    def set_default_project(self, project_key: str) -> None:
        """Mark an existing project as the default."""

    @abstractmethod
    def remove_project(self, project_key: str) -> None:
        """Remove a project; if it was the default, the oldest remaining one takes over."""

    @abstractmethod
    def clear(self) -> None:
        """Remove the connection and all projects; no-op when nothing is stored."""
