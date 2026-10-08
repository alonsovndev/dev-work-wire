import os
from dataclasses import dataclass
from typing import Optional

from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.domain.exceptions import BusinessRuleViolation
from devworkwire.core.ports.jira_config_store import (
    JiraConfigStore,
    JiraProject,
    normalize_project_key,
)

ENV_BASE_URL = "JIRA_BASE_URL"
ENV_EMAIL = "JIRA_EMAIL"
ENV_API_TOKEN = "JIRA_API_TOKEN"

SOURCE_ENV = "env"
SOURCE_DB = "db"
SOURCE_PROJECT_FILE = "devworkwire.yml"
SOURCE_OPTION = "--project"


@dataclass(frozen=True)
class ResolvedValue:
    value: str
    source: str


@dataclass(frozen=True)
class JiraConnection:
    """Effective Jira settings and where each came from.

    Connection values: env > stored config. Project key: ``--project`` > stored
    default project > ``devworkwire.yml``.
    """

    base_url: Optional[ResolvedValue]
    email: Optional[ResolvedValue]
    api_token: Optional[ResolvedValue]
    project_key: Optional[ResolvedValue]
    projects: tuple[JiraProject, ...] = ()
    store_error: Optional[str] = None

    def require_complete(self) -> tuple[str, str, str, str]:
        """Return (base_url, email, api_token, project_key) or raise if any is missing."""
        missing = [
            name
            for name, resolved in (
                ("base URL", self.base_url),
                ("email", self.email),
                ("API token", self.api_token),
                ("project key", self.project_key),
            )
            if resolved is None
        ]
        if missing:
            detail = f" The stored config could not be read: {self.store_error}." if self.store_error else ""
            raise BusinessRuleViolation(
                f"Jira is not configured (missing: {', '.join(missing)}).{detail} "
                "Run `dwire config setup`."
            )
        assert self.base_url and self.email and self.api_token and self.project_key
        return (
            self.base_url.value,
            self.email.value,
            self.api_token.value,
            self.project_key.value,
        )


def resolve_jira_connection(
    store: JiraConfigStore,
    project_config: Optional[ProjectConfig],
    project_override: Optional[str] = None,
) -> JiraConnection:
    # A broken or unreadable store must not break env-only setups.
    store_error = None
    try:
        stored = store.load_credentials()
        projects = store.list_projects()
    except Exception as error:
        stored, projects, store_error = None, [], str(error)

    def pick(env_name: str, stored_value: Optional[str]) -> Optional[ResolvedValue]:
        for source, value in ((SOURCE_ENV, os.environ.get(env_name)), (SOURCE_DB, stored_value)):
            if value and value.strip():
                return ResolvedValue(value.strip(), source)
        return None

    return JiraConnection(
        base_url=pick(ENV_BASE_URL, stored.base_url if stored else None),
        email=pick(ENV_EMAIL, stored.email if stored else None),
        api_token=pick(ENV_API_TOKEN, stored.api_token if stored else None),
        project_key=_resolve_project_key(projects, project_config, project_override),
        projects=tuple(projects),
        store_error=store_error,
    )


def _resolve_project_key(projects, project_config, project_override) -> Optional[ResolvedValue]:
    if project_override is not None:
        key = normalize_project_key(project_override)
        configured = [project.key for project in projects]
        if configured and key not in configured:
            raise BusinessRuleViolation(
                f"Project {key} is not configured (configured: {', '.join(configured)}). "
                f"Add it with `dwire config add-project {key}`."
            )
        return ResolvedValue(key, SOURCE_OPTION)
    default = next((project.key for project in projects if project.is_default), None)
    if default:
        return ResolvedValue(default, SOURCE_DB)
    if project_config and project_config.project_key:
        return ResolvedValue(project_config.project_key.strip(), SOURCE_PROJECT_FILE)
    return None
