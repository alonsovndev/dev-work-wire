"""Connection and resiliency settings for the Jira ``WorkItemProvider`` adapter."""

from dataclasses import dataclass

DEFAULT_API_VERSION = "3"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 4


@dataclass(frozen=True)
class JiraSettings:
    """Immutable settings for one Jira connection."""

    base_url: str
    username: str
    api_token: str
    project_key: str
    api_version: str = DEFAULT_API_VERSION
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    story_points_field: str | None = None
