"""Renders a fetched Epic as a bordered box for CLI display."""

import textwrap

from devworkwire.core.domain.entities import Epic, UserStory

_CONTENT_WIDTH = 76
_NO_DESCRIPTION = "(No description provided.)"


def _wrap_paragraph(paragraph: str) -> list[str]:
    """Wraps one paragraph, hanging bullet-list continuations under the text."""
    if paragraph.startswith("- ") or paragraph.startswith("* "):
        return textwrap.wrap(
            paragraph, width=_CONTENT_WIDTH, subsequent_indent="  "
        )
    return textwrap.wrap(paragraph, width=_CONTENT_WIDTH) or [""]


def _wrap_description(description: str) -> list[str]:
    """Wraps a description into content lines, preserving paragraph breaks."""
    description = description.strip()
    if not description:
        return [_NO_DESCRIPTION]

    lines: list[str] = []
    paragraphs = description.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        if index > 0:
            lines.append("")
        for line in paragraph.split("\n"):
            lines.extend(_wrap_paragraph(line))
    return lines


def _render_panel(kind: str, key: str | None, title: str, description: str, details: list[str]) -> str:
    def row(text: str = "") -> str:
        return f"║  {text.ljust(_CONTENT_WIDTH)}  ║"

    lines = ["╔" + "═" * (_CONTENT_WIDTH + 4) + "╗"]
    if key:
        lines.append(row(f"{kind}: {key}"))
        lines.append(row())
    lines += [row(line) for line in _wrap_paragraph(title)]
    if details:
        lines.append(row())
        for detail in details:
            lines += [row(line) for line in _wrap_paragraph(detail)]
    lines.append(row())
    lines += [row(line) for line in _wrap_description(description)]
    lines.append("╚" + "═" * (_CONTENT_WIDTH + 4) + "╝")
    return "\n".join(lines)


def render_epic_panel(epic: Epic) -> str:
    details = []
    if epic.priority:
        details.append(f"Priority: {epic.priority.name}")
    if epic.labels:
        details.append(f"Labels: {', '.join(label.name for label in epic.labels)}")
    return _render_panel(
        "Epic", epic.issue_id.key if epic.issue_id else None,
        epic.title, epic.description, details,
    )


def render_story_panel(story: UserStory) -> str:
    details = []
    if story.epic_key:
        details.append(f"Epic: {story.epic_key}")
    if story.status:
        details.append(f"Status: {story.status}")
    if story.priority:
        details.append(f"Priority: {story.priority.name}")
    if story.story_points is not None:
        details.append(f"Points: {story.story_points.value}")
    if story.labels:
        details.append(f"Labels: {', '.join(label.name for label in story.labels)}")
    return _render_panel(
        "Story", story.issue_id.key if story.issue_id else None,
        story.title, story.description, details,
    )
