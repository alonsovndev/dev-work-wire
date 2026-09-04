import json
import httpx
import backoff
from typing import Optional

from devworkwire.core.ports.work_item_provider import WorkItemProvider
from devworkwire.core.domain import Epic, IssueId, Priority, Label

def _is_transient_error(e: Exception) -> bool:
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code in {408, 429, 500, 502, 503, 504}
    return isinstance(e, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout))

class JiraProvider(WorkItemProvider):
    def __init__(self, base_url: str, username: str, api_token: str, project_key: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.project_key = project_key

    @backoff.on_exception(
        backoff.expo,
        (httpx.RequestError, httpx.HTTPStatusError),
        max_tries=4,
        giveup=lambda e: not _is_transient_error(e)
    )
    async def fetch_epic(self, key: str) -> Optional[Epic]:
        url = f"{self.base_url}/rest/api/3/issue/{key}"
        auth = (self.username, self.api_token)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, auth=auth)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            
            fields = data.get("fields", {})
            title = fields.get("summary", "")
            
            # Very basic handling of description which in v3 is an Atlassian Document Format (ADF) dict
            desc_field = fields.get("description", {})
            description = json.dumps(desc_field) if isinstance(desc_field, dict) else str(desc_field)
            
            priority_name = fields.get("priority", {}).get("name")
            priority = Priority.from_jira_name(priority_name) if priority_name else None
            
            labels = [Label(name=lbl) for lbl in fields.get("labels", [])]
            
            epic = Epic.create(
                title=title,
                description=description,
                priority=priority,
                labels=labels
            )
            epic.issue_id = IssueId(key=data["key"])
            return epic

    @backoff.on_exception(
        backoff.expo,
        (httpx.RequestError, httpx.HTTPStatusError),
        max_tries=4,
        giveup=lambda e: not _is_transient_error(e)
    )
    async def create_epic(self, epic: Epic) -> str:
        url = f"{self.base_url}/rest/api/3/issue"
        auth = (self.username, self.api_token)
        
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": epic.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": epic.description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Epic"}
            }
        }
        
        if epic.priority:
            payload["fields"]["priority"] = {"name": epic.priority.name}
            
        if epic.labels:
            payload["fields"]["labels"] = [lbl.name for lbl in epic.labels]
            
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, auth=auth)
            response.raise_for_status()
            data = response.json()
            return data["key"]
