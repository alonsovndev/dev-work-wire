"""Per-project DevWorkWire configuration (``devworkwire.yml``).

Declares which provider serves the project, the project key, field mappings,
and transition-name overrides. Secrets never live here; they stay in
environment variables consumed by the provider settings (e.g. ``JiraSettings``).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from pyaml_env import parse_config

from devworkwire.core.domain.exceptions import BusinessRuleViolationException

CONFIG_FILE_NAME = "devworkwire.yml"
SUPPORTED_PROVIDERS = ("jira",)
DEFAULT_FIELD_MAPPINGS = {"story_points": "customfield_10011"}


@dataclass(frozen=True)
class ProjectConfig:
    """Immutable project-level configuration for one DevWorkWire project."""

    provider: str
    project_key: str
    field_mappings: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_FIELD_MAPPINGS)
    )
    transition_overrides: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "ProjectConfig":
        """
        Loads and validates the project configuration file.

        Args:
            path: Explicit config path. Defaults to ``devworkwire.yml`` in
                the current working directory.

        Returns:
            A validated ProjectConfig.

        Raises:
            BusinessRuleViolationException: If the file is missing or the
                content is incomplete/unsupported.
        """
        config_path = Path(path) if path is not None else Path.cwd() / CONFIG_FILE_NAME
        if not config_path.exists():
            raise BusinessRuleViolationException(
                f"Project configuration not found: {config_path}",
                details="Copy devworkwire.example.yml to "
                f"{CONFIG_FILE_NAME} and adjust it for your project.",
            )

        raw = parse_config(path=str(config_path)) or {}
        provider = raw.get("provider")
        project_key = raw.get("project_key")

        if not provider:
            raise BusinessRuleViolationException(
                "Project configuration is incomplete",
                details=f"'provider' is required in {CONFIG_FILE_NAME} "
                f"(supported: {', '.join(SUPPORTED_PROVIDERS)})",
            )
        if provider not in SUPPORTED_PROVIDERS:
            raise BusinessRuleViolationException(
                f"Unsupported provider: {provider}",
                details=f"supported providers: {', '.join(SUPPORTED_PROVIDERS)}",
            )
        if not project_key:
            raise BusinessRuleViolationException(
                "Project configuration is incomplete",
                details=f"'project_key' is required in {CONFIG_FILE_NAME}",
            )

        field_mappings = {
            **DEFAULT_FIELD_MAPPINGS,
            **(raw.get("field_mappings") or {}),
        }
        transition_overrides = raw.get("transition_overrides") or {}

        return cls(
            provider=provider,
            project_key=project_key,
            field_mappings=field_mappings,
            transition_overrides=transition_overrides,
        )
