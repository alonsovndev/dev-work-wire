from devworkwire.config.app_config import AppConfig
from devworkwire.config.project_config import ProjectConfig
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider
from devworkwire.infrastructure.external.jira.settings import (
    DEFAULT_API_VERSION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    JiraSettings,
)


class Container:
    def __init__(self):
        self._jira_provider = None

    def get_jira_provider(self) -> JiraProvider:
        if not self._jira_provider:
            app_config = AppConfig.instance()
            project_config = ProjectConfig.load()
            settings = JiraSettings(
                base_url=app_config.get_config("jira.base_url"),
                username=app_config.get_config("jira.email"),
                api_token=app_config.get_config("jira.api_token"),
                project_key=project_config.project_key,
                api_version=app_config.get_config("jira.api_version", default=DEFAULT_API_VERSION),
                timeout=app_config.get_config("jira.timeout", default=DEFAULT_TIMEOUT_SECONDS),
                max_retries=app_config.get_config("jira.max_retries", default=DEFAULT_MAX_RETRIES),
            )
            self._jira_provider = JiraProvider(settings)
        return self._jira_provider
