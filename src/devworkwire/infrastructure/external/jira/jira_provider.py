import json
from typing import Optional

import backoff
import httpx

from devworkwire.core.domain import Epic, IssueId, Label, Priority
from devworkwire.core.ports.work_item_provider import WorkItemProvider
from devworkwire.infrastructure.external.jira.settings import JiraSettings


def _is_transient_error(error: Exception) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in {408, 429, 500, 502, 503, 504}
    return isinstance(error, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout))


class JiraProvider(WorkItemProvider):
    def __init__(self, settings: JiraSettings):
        self.settings = settings
        retry = backoff.on_exception(
            backoff.expo,
            (httpx.RequestError, httpx.HTTPStatusError),
            max_tries=settings.max_retries,
            giveup=lambda e: not _is_transient_error(e),
        )
        self._fetch_epic_with_retry = retry(self._fetch_epic)
        self._create_epic_with_retry = retry(self._create_epic)

    @property
    def _issue_url(self) -> str:
        return f"{self.settings.base_url}/rest/api/{self.settings.api_version}/issue"

    async def fetch_epic(self, key: str) -> Optional[Epic]:
        return await self._fetch_epic_with_retry(key)

    async def create_epic(self, epic: Epic) -> str:
        return await self._create_epic_with_retry(epic)

    async def _fetch_epic(self, key: str) -> Optional[Epic]:
        auth = (self.settings.username, self.settings.api_token)
        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.get(f"{self._issue_url}/{key}", auth=auth)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

            fields = data.get("fields", {})
            title = fields.get("summary", "")

            # Jira v3 returns description as an Atlassian Document Format (ADF) dict.
            desc_field = fields.get("description", {})
            description = json.dumps(desc_field) if isinstance(desc_field, dict) else str(desc_field)

            priority_name = fields.get("priority", {}).get("name")
            priority = Priority.from_jira_name(priority_name) if priority_name else None

            labels = [Label(name=lbl) for lbl in fields.get("labels", [])]

            epic = Epic.create(
                title=title,
                description=description,
                priority=priority,
                labels=labels,
            )
            epic.issue_id = IssueId(key=data["key"])
            return epic

    async def _create_epic(self, epic: Epic) -> str:
        auth = (self.settings.username, self.settings.api_token)

        payload = {
            "fields": {
                "project": {"key": self.settings.project_key},
                "summary": epic.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": epic.description}],
                        }
                    ],
                },
                "issuetype": {"name": "Epic"},
            }
        }

        if epic.priority:
            payload["fields"]["priority"] = {"name": epic.priority.name}

        if epic.labels:
            payload["fields"]["labels"] = [lbl.name for lbl in epic.labels]

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.post(self._issue_url, json=payload, auth=auth)
            response.raise_for_status()
            data = response.json()
            return data["key"]
