import os
import re
from devworkwire.core.domain import Epic, Label, Priority, StoryPoints, UserStory

_STORY_HEADING_RE = re.compile(r"^###[ \t]+[^:\s][^:\n]*:[ \t]*(\S.*)$", re.MULTILINE)


def parse_epic_markdown(file_path: str) -> Epic:
    """
    Parses an epic markdown file into an Epic.
    Expected format:
    # Epic: [Title]
    **Priority**: [priority]
    **Labels**: [label1, label2]
    ...
    **Epic Description:**
    [description, up to the next `##` heading or end of file]
    """
    return _parse_epic_content(_read_required_file(file_path))


def _parse_epic_content(content: str) -> Epic:
    title_match = re.search(r"^# Epic:[ \t]*(\S.*)$", content, re.MULTILINE)
    desc_match = re.search(
        r"\*\*Epic Description:\*\*\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL
    )
    priority_match = re.search(r"\*\*Priority\*\*:[ \t]*(\S.*)$", content, re.MULTILINE)
    labels_match = re.search(r"\*\*Labels\*\*:[ \t]*(\S.*)$", content, re.MULTILINE)

    title = title_match.group(1).strip() if title_match else "Untitled Epic"
    description = desc_match.group(1).strip() if desc_match else ""
    priority = Priority.from_jira_name(priority_match.group(1).strip()) if priority_match else None
    labels = _parse_labels(labels_match)

    return Epic.create(
        title=title,
        description=description,
        priority=priority,
        labels=labels
    )


def parse_stories_markdown(file_path: str) -> list[UserStory]:
    """
    Parses a stories markdown file into a list of UserStory entities.
    Stories are optional: a missing file yields an empty list.

    Each story is a block starting with a `### <Story ID>: <Title>` heading:
    **Priority**: [priority]
    **Effort Estimate**: [story points]
    **Labels**: [label1, label2]
    **As a** ..., **I want to** ..., **So that** ...
    **Acceptance Criteria**:
    - [ ] ...
    """
    if not os.path.exists(file_path):
        return []

    content = _read_required_file(file_path)

    headings = list(_STORY_HEADING_RE.finditer(content))
    stories = []
    for index, heading in enumerate(headings):
        block_start = heading.start()
        block_end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        stories.append(_parse_story_block(heading.group(1).strip(), content[block_start:block_end]))

    return stories


def _parse_story_block(title: str, block: str) -> UserStory:
    priority_match = re.search(r"\*\*Priority\*\*:[ \t]*(\S.*)$", block, re.MULTILINE)
    points_match = re.search(r"\*\*Effort Estimate\*\*:[ \t]*(\d+)$", block, re.MULTILINE)
    labels_match = re.search(r"\*\*Labels\*\*:[ \t]*(\S.*)$", block, re.MULTILINE)

    priority = Priority.from_jira_name(priority_match.group(1).strip()) if priority_match else None
    story_points = StoryPoints(value=int(points_match.group(1))) if points_match else None
    labels = _parse_labels(labels_match)

    return UserStory.create(
        title=title,
        description=_build_story_description(block),
        priority=priority,
        story_points=story_points,
        labels=labels,
    )


def _build_story_description(block: str) -> str:
    narrative_match = re.search(
        r"(\*\*As a\*\*.*?\*\*So that\*\*.*?)(?=\n\n|\*\*Acceptance Criteria\*\*|\Z)",
        block,
        re.DOTALL,
    )
    criteria_match = re.search(
        r"\*\*Acceptance Criteria\*\*:\s*\n(.*?)(?=\n\*\*|\n---|\Z)", block, re.DOTALL
    )

    parts = []
    if narrative_match:
        parts.append(narrative_match.group(1).strip())
    if criteria_match:
        parts.append("**Acceptance Criteria**:\n" + criteria_match.group(1).strip())

    return "\n\n".join(parts)


def _parse_labels(labels_match: "re.Match[str] | None") -> list[Label]:
    if not labels_match:
        return []
    labels_raw = labels_match.group(1).strip()
    return [Label(name=lbl.strip()) for lbl in labels_raw.split(",") if lbl.strip()]


def _read_required_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    with open(file_path, "r") as f:
        return f.read()
