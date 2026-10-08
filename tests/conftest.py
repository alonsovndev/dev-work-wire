import pytest

from devworkwire.config.paths import Paths
from devworkwire.core.domain.exceptions import BusinessRuleViolation

from devworkwire.core.ports.jira_config_store import (
    JiraConfigStore,
    JiraProject,
    normalize_project_key,
)


class FakeJiraConfigStore(JiraConfigStore):
    def __init__(self, credentials=None, projects=(), default=None):
        self.credentials = credentials
        self.projects = [normalize_project_key(key) for key in projects]
        self.default = default or (self.projects[0] if self.projects else None)

    def load_credentials(self):
        return self.credentials

    def save_credentials(self, credentials):
        self.credentials = credentials

    def list_projects(self):
        return [JiraProject(key, key == self.default) for key in self.projects]

    def add_project(self, project_key, make_default=False):
        key = normalize_project_key(project_key)
        if key not in self.projects:
            self.projects.append(key)
        if make_default or self.default is None:
            self.default = key

    def set_default_project(self, project_key):
        key = normalize_project_key(project_key)
        if key not in self.projects:
            raise BusinessRuleViolation(f"Project {key} is not configured.")
        self.default = key

    def remove_project(self, project_key):
        key = normalize_project_key(project_key)
        if key not in self.projects:
            raise BusinessRuleViolation(f"Project {key} is not configured.")
        self.projects.remove(key)
        if self.default == key:
            self.default = self.projects[0] if self.projects else None

    def clear(self):
        self.credentials, self.projects, self.default = None, [], None


@pytest.fixture
def fake_store():
    """Factory: ``fake_store(credentials=None, projects=(), default=None)``."""
    return FakeJiraConfigStore


@pytest.fixture(autouse=True)
def isolated_user_config(tmp_path_factory, monkeypatch):
    """Keep every test away from the developer's real ~/.config, .env and Jira environment."""
    monkeypatch.setenv("DEVWORKWIRE_CONFIG_DIR", str(tmp_path_factory.mktemp("user-config")))
    monkeypatch.setattr(Paths, "ENV_FILE_PATH", tmp_path_factory.mktemp("no-env") / ".env")
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
