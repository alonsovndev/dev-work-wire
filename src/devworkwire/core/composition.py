from devworkwire.config.app_config import AppConfig
from devworkwire.config.project_config import ProjectConfig
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider


class Container:
    def __init__(self):
        self._jira_provider = None

    def get_jira_provider(self) -> JiraProvider:
        if not self._jira_provider:
            app_config = AppConfig.instance()
            project_config = ProjectConfig.load()
            self._jira_provider = JiraProvider(
                base_url=app_config.get_config("jira.base_url"),
                username=app_config.get_config("jira.email"),
                api_token=app_config.get_config("jira.api_token"),
                project_key=project_config.project_key,
            )
        return self._jira_provider
