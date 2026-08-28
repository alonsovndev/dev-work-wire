"""Jira implementation of the WorkItemProvider port.

Single Jira REST adapter for all work-item operations (epics and stories),
so provider-specific behavior lives in one place behind the port.
"""

from typing import List, Optional

import httpx

from devworkwire.application.ports import WorkItemProvider
from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.domain.exceptions import (
    BusinessRuleViolationException,
    UnauthorizedWorkspaceAccess,
)
from devworkwire.core.domain.issue import IssueStatus
from devworkwire.core.domain.value_objects import IssueId
from devworkwire.features.epic.domain import Epic
from devworkwire.features.story.domain import UserStory
from devworkwire.infrastructure.external.jira.parsing import parse_jira_datetime
from devworkwire.infrastructure.external.jira.settings import JiraSettings
from devworkwire.shared.log_config import get_logger

logger = get_logger(__name__)


def map_epic(data: dict, story_points_field: str) -> Epic:
    """
    Map Jira API response data to the Epic domain entity.

    Args:
        data: Jira API response data.
        story_points_field: Custom field id holding story points.

    Returns:
        The mapped Epic entity.
    """
    fields = data["fields"]
    return Epic.create(
        key=data["key"],
        numeric_id=int(data["id"]),
        summary=fields.get("summary", ""),
        description=fields.get("description", ""),
        status=IssueStatus.from_jira_status(fields["status"]["name"]),
        created_at=parse_jira_datetime(fields["created"]),
        updated_at=parse_jira_datetime(fields["updated"]),
        reporter=fields.get("reporter", {}).get("displayName"),
        priority=fields.get("priority", {}).get("name")
        if fields.get("priority")
        else None,
        labels=fields.get("labels", []),
        story_points=fields.get(story_points_field),
    )


def map_user_story(
    data: dict, story_points_field: str, epic_key: Optional[str] = None
) -> UserStory:
    """
    Map a Jira API issue response to the UserStory domain entity.

    Args:
        data: Jira API issue data.
        story_points_field: Custom field id holding story points.
        epic_key: Parent epic key when known from the query context.

    Returns:
        The mapped UserStory entity.
    """
    fields = data["fields"]
    return UserStory.create(
        key=data["key"],
        numeric_id=int(data["id"]),
        summary=fields.get("summary", ""),
        description=fields.get("description", ""),
        status=IssueStatus.from_jira_status(fields["status"]["name"]),
        created_at=parse_jira_datetime(fields["created"]),
        updated_at=parse_jira_datetime(fields["updated"]),
        reporter=fields.get("reporter", {}).get("displayName"),
        priority=fields["priority"]["name"] if fields.get("priority") else None,
        labels=fields.get("labels", []),
        story_points=fields.get(story_points_field),
        epic_key=epic_key,
    )


class JiraWorkItemProvider(WorkItemProvider):
    """Jira REST adapter for the WorkItemProvider port."""

    def __init__(self, settings: JiraSettings, project_config: ProjectConfig):
        """
        Initializes the adapter with connection settings and project config.

        Args:
            settings: Validated Jira connection settings (secrets included).
            project_config: Project key and field mappings for this project.
        """
        self.settings = settings
        self.project_config = project_config

    @property
    def _story_points_field(self) -> str:
        return self.project_config.field_mappings["story_points"]

    async def get_epic(self, issue_id: IssueId) -> Optional[Epic]:
        """
        Retrieve details of an epic by its key from Jira.

        Args:
            issue_id: The IssueId of the epic to retrieve.

        Returns:
            The Epic domain entity.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        url = f"{self.settings.base_url}/rest/api/3/issue/{issue_id.key}"
        # Never log credentials or full API bodies; they can contain PII.
        logger.info("Fetching epic from Jira", extra={"issue_key": issue_id.key})

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.get(
                url,
                auth=(self.settings.email, self.settings.api_token),
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        data = response.json()

        return map_epic(data, self._story_points_field)

    async def create_epic(self, summary: str, description: str) -> Epic:
        """
        Create a new Epic in the configured Jira project.

        Args:
            summary: Summary of the epic.
            description: Description of the epic.

        Returns:
            The created Epic.

        Raises:
            BusinessRuleViolationException: If the creation fails due to
                invalid input or configuration.
        """
        url = f"{self.settings.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": self.project_config.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description.strip()}],
                        }
                    ],
                },
                "issuetype": {"name": "Epic"},
            }
        }

        logger.info(
            "Creating a new Epic in Jira",
            extra={"project_key": self.project_config.project_key},
        )

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.post(
                url,
                auth=(self.settings.email, self.settings.api_token),
                json=payload,
            )

        if response.status_code != 201:
            # Jira error bodies are not guaranteed to be valid JSON.
            try:
                error_body = response.json()
            except ValueError:
                error_body = {}
            error_message = error_body.get("errorMessages", ["Unknown error"])
            logger.error(
                "Failed to create Epic in Jira",
                extra={"status_code": response.status_code},
            )
            raise BusinessRuleViolationException(
                f"Failed to create an Epic: {error_message}",
                details=error_body.get("errors", {}),
            )

        data = response.json()
        logger.info(
            "Epic successfully created in Jira",
            extra={"issue_key": data.get("key")},
        )

        return map_epic(data, self._story_points_field)

    async def find_epics_by_project(self, project_key: str) -> List[Epic]:
        """
        Finds all Epics within a given project.

        Args:
            project_key: The Jira project key.

        Returns:
            A list of Epic entities.

        Raises:
            UnauthorizedWorkspaceAccess: If the requested project differs
                from the configured one.
        """
        if project_key != self.project_config.project_key:
            raise UnauthorizedWorkspaceAccess(
                project_key, self.project_config.project_key
            )
        return []

    async def get_stories_in_epic(self, epic_id: IssueId) -> List[UserStory]:
        """
        Retrieve all user stories whose parent is the given epic.

        Args:
            epic_id: The IssueId of the parent epic.

        Returns:
            List of UserStory entities (empty when the epic has no stories).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        url = f"{self.settings.base_url}/rest/api/3/search"
        # POST is used because GET /search is deprecated on Jira Cloud v3.
        # 'parent = KEY' JQL matches stories under an epic for both
        # company-managed and team-managed projects.
        payload = {
            "jql": f"parent = {epic_id.key}",
            "maxResults": 100,
            "fields": [
                "summary",
                "description",
                "status",
                "created",
                "updated",
                "reporter",
                "priority",
                "labels",
                self._story_points_field,
            ],
        }
        logger.info("Fetching stories for epic", extra={"issue_key": epic_id.key})

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.post(
                url,
                auth=(self.settings.email, self.settings.api_token),
                json=payload,
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        issues = response.json().get("issues", [])

        stories = [
            map_user_story(issue, self._story_points_field, epic_key=epic_id.key)
            for issue in issues
        ]
        logger.info(
            "Fetched stories for epic",
            extra={"issue_key": epic_id.key, "count": len(stories)},
        )
        return stories

    # ── S3: import-flow methods ────────────────────────────────────────

    async def find_epic_by_key(self, key: str) -> Optional[Epic]:
        """Find an epic by its Jira issue key (e.g. ``OPH-42``)."""
        url = f"{self.settings.base_url}/rest/api/3/issue/{key}"
        logger.info("Finding epic by key", extra={"issue_key": key})

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.get(
                url,
                auth=(self.settings.email, self.settings.api_token),
                headers={"Accept": "application/json"},
            )

        if response.status_code == 404:
            return None
        response.raise_for_status()
        return map_epic(response.json(), self._story_points_field)

    async def create_user_story(
        self, epic_key: str, summary: str, description: str
    ) -> UserStory:
        """Create a user story linked to the given epic."""
        url = f"{self.settings.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": self.project_config.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description.strip()}],
                        }
                    ],
                },
                "issuetype": {"name": "Story"},
                "parent": {"key": epic_key},
            }
        }

        logger.info(
            "Creating user story in Jira",
            extra={
                "epic_key": epic_key,
                "project_key": self.project_config.project_key,
            },
        )

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.post(
                url,
                auth=(self.settings.email, self.settings.api_token),
                json=payload,
            )

        if response.status_code != 201:
            try:
                error_body = response.json()
            except ValueError:
                error_body = {}
            error_message = error_body.get("errorMessages", ["Unknown error"])
            logger.error(
                "Failed to create user story in Jira",
                extra={"status_code": response.status_code},
            )
            raise BusinessRuleViolationException(
                f"Failed to create a User Story: {error_message}",
                details=error_body.get("errors", {}),
            )

        data = response.json()
        logger.info(
            "User story created in Jira",
            extra={"issue_key": data.get("key")},
        )
        return map_user_story(data, self._story_points_field, epic_key=epic_key)

    async def update_epic(
        self, issue_id: IssueId, summary: str, description: str
    ) -> Epic:
        """Update an existing epic's summary and description."""
        url = f"{self.settings.base_url}/rest/api/3/issue/{issue_id.key}"
        payload = {
            "fields": {
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description.strip()}],
                        }
                    ],
                },
            }
        }

        logger.info("Updating epic in Jira", extra={"issue_key": issue_id.key})

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.put(
                url,
                auth=(self.settings.email, self.settings.api_token),
                json=payload,
            )

        if response.status_code not in (200, 204):
            try:
                error_body = response.json()
            except ValueError:
                error_body = {}
            error_message = error_body.get("errorMessages", ["Unknown error"])
            raise BusinessRuleViolationException(
                f"Failed to update Epic {issue_id.key}: {error_message}",
                details=error_body.get("errors", {}),
            )

        logger.info("Epic updated in Jira", extra={"issue_key": issue_id.key})
        # Re-fetch to return the updated entity.
        epic = await self.get_epic(issue_id)
        if epic is None:
            raise BusinessRuleViolationException(
                f"Epic {issue_id.key} not found after update",
                details="The epic may have been deleted during the update.",
            )
        return epic
