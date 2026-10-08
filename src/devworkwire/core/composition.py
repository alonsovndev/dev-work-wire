from typing import Optional

from devworkwire.config.app_config import AppConfig
from devworkwire.config.jira_connection import JiraConnection, resolve_jira_connection
from devworkwire.config.project_config import DEFAULT_FIELD_MAPPINGS, ProjectConfig
from devworkwire.core.ports.jira_config_store import JiraConfigStore
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider
from devworkwire.infrastructure.external.jira.settings import (
    DEFAULT_API_VERSION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    JiraSettings,
)
from devworkwire.infrastructure.local.store.sqlite_jira_config_store import (
    SqliteJiraConfigStore,
)


class Container:
    def __init__(self, config_store: Optional[JiraConfigStore] = None):
        self._jira_provider: Optional[JiraProvider] = None
        self._project_override: Optional[str] = None
        self.config_store: JiraConfigStore = config_store or SqliteJiraConfigStore()

    def select_project(self, project_key: Optional[str]) -> None:
        """Use this project instead of the stored default for later provider requests."""
        if project_key != self._project_override:
            self._project_override = project_key
            self.reset()

    def reset(self) -> None:
        """Drop the cached provider so the next request re-reads configuration."""
        self._jira_provider = None

    def resolve_jira_connection(self) -> tuple[JiraConnection, Optional[ProjectConfig]]:
        # AppConfig.instance() loads .env into the environment as a side effect.
        AppConfig.instance()
        project_config = ProjectConfig.load_if_present()
        connection = resolve_jira_connection(
            self.config_store, project_config, self._project_override
        )
        return connection, project_config

    def get_jira_provider(self) -> JiraProvider:
        if self._jira_provider is None:
            app_config = AppConfig.instance()
            connection, project_config = self.resolve_jira_connection()
            base_url, email, api_token, project_key = connection.require_complete()
            field_mappings = (
                project_config.field_mappings if project_config else DEFAULT_FIELD_MAPPINGS
            )
            settings = JiraSettings(
                base_url=base_url,
                username=email,
                api_token=api_token,
                project_key=project_key,
                api_version=app_config.get_config("jira.api_version", default=DEFAULT_API_VERSION),
                timeout=app_config.get_config("jira.timeout", default=DEFAULT_TIMEOUT_SECONDS),
                max_retries=app_config.get_config("jira.max_retries", default=DEFAULT_MAX_RETRIES),
                story_points_field=field_mappings.get("story_points"),
            )
            self._jira_provider = JiraProvider(settings)
        return self._jira_provider
