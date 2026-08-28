"""Connection settings for the Jira REST API.

Centralizes configuration loading and validation so every feature adapter
starts from the same, already-validated settings object instead of each
adapter re-parsing the raw config dictionary.
"""

from dataclasses import dataclass

from devworkwire.config.app_config import AppConfig
from devworkwire.core.domain.exceptions import BusinessRuleViolationException

_REQUIRED_KEYS = ("base_url", "email", "api_token")


@dataclass(frozen=True)
class JiraSettings:
    """Immutable Jira connection settings.

    Project selection lives in ``ProjectConfig`` (devworkwire.yml); this
    object only carries connection details and secrets.
    """

    base_url: str
    email: str
    api_token: str
    timeout: float = 30.0

    @classmethod
    def from_dict(cls, jira_config: dict) -> "JiraSettings":
        """
        Builds settings from a raw config dictionary.

        Raises:
            BusinessRuleViolationException: If required entries are missing.
        """
        missing = [key for key in _REQUIRED_KEYS if not jira_config.get(key)]
        if missing:
            raise BusinessRuleViolationException(
                "Jira configuration is incomplete",
                details=f"missing: {', '.join(missing)}",
            )
        return cls(
            base_url=jira_config["base_url"],
            email=jira_config["email"],
            api_token=jira_config["api_token"],
            timeout=float(jira_config.get("timeout", 30)),
        )

    @classmethod
    def from_config(cls) -> "JiraSettings":
        """Loads settings from the ``jira`` section of the app configuration."""
        jira_config = AppConfig.instance().get_config("jira")
        return cls.from_dict(jira_config)
