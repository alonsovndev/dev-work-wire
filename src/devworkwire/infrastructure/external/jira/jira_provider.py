from typing import Optional

import backoff
import httpx

from devworkwire.core.domain import Epic, IssueId, Label, Priority, UserStory
from devworkwire.core.ports.work_item_provider import WorkItemProvider
from devworkwire.infrastructure.external.jira.settings import JiraSettings


def _is_transient_error(error: Exception) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in {408, 429, 500, 502, 503, 504}
    return isinstance(error, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout))


def _adf_text(node: dict) -> str:
    """Concatenated text of an ADF ``text`` node and any nested text nodes."""
    if node.get("type") == "text":
        return node.get("text", "")
    return "".join(_adf_text(child) for child in node.get("content", []))


def _adf_to_text(doc: dict) -> str:
    """Renders an Atlassian Document Format doc as plain, readable text.

    Handles the node types Jira commonly uses in Epic descriptions
    (paragraphs and bullet/ordered lists); unsupported node types are
    skipped rather than raising.
    """
    blocks = []
    for node in doc.get("content", []):
        node_type = node.get("type")
        if node_type == "paragraph":
            blocks.append(_adf_text(node))
        elif node_type in ("bulletList", "orderedList"):
            items = [
                f"- {_adf_text(item)}" for item in node.get("content", [])
            ]
            blocks.append("\n".join(items))
    return "\n\n".join(block for block in blocks if block)


def _raise_for_status_with_jira_detail(response: httpx.Response) -> None:
    """Like ``response.raise_for_status()``, but folds Jira's error body
    (``errorMessages``/``errors``) into the exception message — the bare
    status code alone isn't actionable for a 400 field-validation failure.
    """
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = None
        try:
            body = response.json()
            parts = list(body.get("errorMessages", []))
            parts += [f"{field}: {msg}" for field, msg in body.get("errors", {}).items()]
            detail = "; ".join(parts) if parts else None
        except ValueError:
            detail = response.text or None
        if detail:
            raise httpx.HTTPStatusError(
                f"{error}. Jira response: {detail}", request=error.request, response=error.response
            ) from error
        raise


_MOSCOW_TO_JIRA_PRIORITY = {
    "Must Have": "Highest",
    "Should Have": "High",
    "Could Have": "Medium",
    "Won't Have": "Low",
}


def _jira_priority_name(priority: Priority) -> str:
    """Maps MoSCoW priority wording (used in epic.md/stories.md) to Jira
    Cloud's default priority scheme. A priority name that isn't a MoSCoW
    term (e.g. already 'High') passes through unchanged, so this doesn't
    break projects/files that use Jira-native priority names directly.
    """
    return _MOSCOW_TO_JIRA_PRIORITY.get(priority.name, priority.name)


def _text_to_adf(text: str) -> dict:
    """Wraps plain text as a single-paragraph Atlassian Document Format doc."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


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
        self._create_story_with_retry = retry(self._create_story)

    @property
    def _issue_url(self) -> str:
        return f"{self.settings.base_url}/rest/api/{self.settings.api_version}/issue"

    async def fetch_epic(self, key: str) -> Optional[Epic]:
        return await self._fetch_epic_with_retry(key)

    async def create_epic(self, epic: Epic) -> str:
        return await self._create_epic_with_retry(epic)

    async def create_story(self, story: UserStory, epic_key: str) -> str:
        return await self._create_story_with_retry(story, epic_key)

    async def _fetch_epic(self, key: str) -> Optional[Epic]:
        auth = (self.settings.username, self.settings.api_token)
        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.get(f"{self._issue_url}/{key}", auth=auth)
            if response.status_code == 404:
                return None
            _raise_for_status_with_jira_detail(response)
            data = response.json()

            fields = data.get("fields", {})
            title = fields.get("summary", "")

            # Jira v3 returns description as an Atlassian Document Format (ADF) dict.
            desc_field = fields.get("description", {})
            description = _adf_to_text(desc_field) if isinstance(desc_field, dict) else str(desc_field)

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
                "description": _text_to_adf(epic.description),
                "issuetype": {"name": "Epic"},
            }
        }

        if epic.priority:
            payload["fields"]["priority"] = {"name": _jira_priority_name(epic.priority)}

        if epic.labels:
            payload["fields"]["labels"] = [lbl.name for lbl in epic.labels]

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.post(self._issue_url, json=payload, auth=auth)
            _raise_for_status_with_jira_detail(response)
            data = response.json()
            return data["key"]

    async def _create_story(self, story: UserStory, epic_key: str) -> str:
        auth = (self.settings.username, self.settings.api_token)

        payload = {
            "fields": {
                "project": {"key": self.settings.project_key},
                "summary": story.title,
                "description": _text_to_adf(story.description),
                "issuetype": {"name": "Story"},
                "parent": {"key": epic_key},
            }
        }

        if story.priority:
            payload["fields"]["priority"] = {"name": _jira_priority_name(story.priority)}

        if story.labels:
            payload["fields"]["labels"] = [lbl.name for lbl in story.labels]

        async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
            response = await client.post(self._issue_url, json=payload, auth=auth)
            _raise_for_status_with_jira_detail(response)
            data = response.json()
            return data["key"]
