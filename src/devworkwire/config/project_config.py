"""Per-project DevWorkWire configuration (``devworkwire.yml``).

Declares which provider serves the project, an optional project key (the
``dwire config`` default project and ``--project`` take precedence), field
mappings, and transition-name overrides. Secrets never live here; they stay in
environment variables consumed via ``AppConfig``.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from pyaml_env import parse_config

from devworkwire.core.domain.exceptions import BusinessRuleViolation

CONFIG_FILE_NAME = "devworkwire.yml"
SUPPORTED_PROVIDERS = ("jira",)
DEFAULT_FIELD_MAPPINGS = {"story_points": "customfield_10011"}


@dataclass(frozen=True)
class ProjectConfig:
    """Immutable project-level configuration for one DevWorkWire project."""

    provider: str
    project_key: Optional[str] = None
    field_mappings: Dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_FIELD_MAPPINGS)
    )
    transition_overrides: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def load_if_present(cls, path: Optional[Path] = None) -> Optional["ProjectConfig"]:
        """Like ``load`` but returns None when the config file does not exist."""
        config_path = Path(path) if path is not None else Path.cwd() / CONFIG_FILE_NAME
        return cls.load(config_path) if config_path.exists() else None

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
            BusinessRuleViolation: If the file is missing or the
                content is incomplete/unsupported.
        """
        config_path = Path(path) if path is not None else Path.cwd() / CONFIG_FILE_NAME
        if not config_path.exists():
            raise BusinessRuleViolation(
                f"Project configuration not found: {config_path}. "
                f"Copy devworkwire.example.yml to {CONFIG_FILE_NAME} and adjust it for your project."
            )

        raw = parse_config(path=str(config_path)) or {}
        provider = raw.get("provider")
        project_key = raw.get("project_key")

        if not provider:
            raise BusinessRuleViolation(
                "Project configuration is incomplete: 'provider' is required in "
                f"{CONFIG_FILE_NAME} (supported: {', '.join(SUPPORTED_PROVIDERS)})"
            )
        if provider not in SUPPORTED_PROVIDERS:
            raise BusinessRuleViolation(
                f"Unsupported provider: {provider} (supported: {', '.join(SUPPORTED_PROVIDERS)})"
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
