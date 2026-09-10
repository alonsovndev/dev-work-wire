"""Renders a fetched Epic as a bordered box for CLI display."""

import textwrap

from devworkwire.core.domain.entities import Epic

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


def render_epic_panel(epic: Epic) -> str:
    """The bordered box showing a fetched epic's key, title, and description."""

    def row(text: str = "") -> str:
        return f"║  {text.ljust(_CONTENT_WIDTH)}  ║"

    lines = ["╔" + "═" * (_CONTENT_WIDTH + 4) + "╗"]
    if epic.issue_id:
        lines.append(row(f"Epic: {epic.issue_id.key}"))
        lines.append(row())
    lines += [row(line) for line in _wrap_paragraph(epic.title)]
    lines.append(row())
    lines += [row(line) for line in _wrap_description(epic.description)]
    lines.append("╚" + "═" * (_CONTENT_WIDTH + 4) + "╝")
    return "\n".join(lines)
