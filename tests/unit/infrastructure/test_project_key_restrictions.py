import pytest

from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.domain.exceptions import UnauthorizedWorkspaceAccess
from devworkwire.infrastructure.external.jira.settings import JiraSettings
from devworkwire.infrastructure.external.jira.work_item_provider import (
    JiraWorkItemProvider,
)


@pytest.fixture
def jira_provider():
    """
    Test fixture to initialize JiraWorkItemProvider with a mocked configuration.
    """
    settings = JiraSettings.from_dict(
        {
            "base_url": "https://test-jira.atlassian.net",
            "email": "test@example.com",
            "api_token": "test_key",
        }
    )
    project_config = ProjectConfig(provider="jira", project_key="OPH")
    return JiraWorkItemProvider(settings, project_config)


@pytest.mark.asyncio
async def test_project_key_restrictions(jira_provider):
    """
    Ensure the provider prevents operations for unauthorized project keys.
    """
    # Arrange
    valid_project_key = "OPH"
    invalid_project_key = "INVALID"

    # Attempting to interact with an invalid project key should raise an exception
    with pytest.raises(UnauthorizedWorkspaceAccess):
        await jira_provider.find_epics_by_project(invalid_project_key)

    # Interacting with the valid project key should NOT raise any exceptions
    try:
        await jira_provider.find_epics_by_project(valid_project_key)
    except UnauthorizedWorkspaceAccess:
        pytest.fail("UnauthorizedWorkspaceAccess was raised for the valid project key.")
