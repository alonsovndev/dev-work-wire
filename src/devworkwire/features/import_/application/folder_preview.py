import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from devworkwire.core.domain import Epic, Label, UserStory
from devworkwire.core.domain.exceptions import BusinessRuleViolation
from devworkwire.features.import_.application.markdown_parser import (
    _parse_epic_content,
    _parse_story_block,
)

_EPIC_HEADING = re.compile(r"^# Epic:[ \t]*(\S.*)$", re.MULTILINE)
_STORY_HEADING = re.compile(r"^###[ \t]+([^:\s][^:\n]*):[ \t]*(\S.*)$")
_STORY_MARKER = re.compile(r"^###(?!#)[^\n]*$", re.MULTILINE)
_WRONG_LEVEL_HEADING = re.compile(
    r"^#{1,2}(?!#)[^\n]*$|^#{4,6}[ \t]+[^:\n]+:[^\n]*$", re.MULTILINE
)
_FIELD = re.compile(r"^\*\*(Priority|Labels|Effort Estimate)\*\*:[ \t]*(.*)$")


@dataclass(frozen=True)
class ValidationIssue:
    file: str
    line: int | None
    message: str

    def __str__(self) -> str:
        location = f"{self.file}:{self.line}" if self.line is not None else self.file
        return f"{location}: {self.message}"


@dataclass(frozen=True)
class StoryPreview:
    story_id: str
    title: str
    line: int
    item: UserStory | None
    source_hash: str


@dataclass(frozen=True)
class FolderPreview:
    epic_title: str | None
    epic: Epic | None
    epic_hash: str | None
    stories: list[StoryPreview]
    errors: list[ValidationIssue]


def _read_file(path: Path, errors: list[ValidationIssue]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        errors.append(ValidationIssue(path.name, None, str(error)))
        return None


def _validate_fields(
    content: str, file: str, start_line: int, errors: list[ValidationIssue]
) -> None:
    for offset, line in enumerate(content.splitlines()):
        line_number = start_line + offset
        field = _FIELD.fullmatch(line)
        if field is None:
            if re.match(r"^\*\*(Priority|Labels|Effort Estimate)\*\*", line):
                errors.append(ValidationIssue(file, line_number, "Malformed field; expected ':'"))
            continue
        name, value = field.groups()
        value = value.strip()
        if name == "Priority" and not value:
            errors.append(ValidationIssue(file, line_number, "Priority cannot be empty"))
        elif name == "Effort Estimate" and file == "stories.md":
            if not re.fullmatch(r"\d+", value):
                errors.append(ValidationIssue(file, line_number, "Effort Estimate must be a nonnegative integer"))
        elif name == "Labels":
            for label_name in value.split(","):
                if not label_name.strip():
                    errors.append(ValidationIssue(file, line_number, "Label name cannot be empty"))
                    continue
                try:
                    Label(name=label_name.strip())
                except ValueError as error:
                    errors.append(ValidationIssue(file, line_number, str(error)))


def preview_folder(folder_path: str) -> FolderPreview:
    folder = Path(folder_path)
    errors: list[ValidationIssue] = []
    stories: list[StoryPreview] = []
    epic: Epic | None = None
    epic_title: str | None = None
    epic_hash: str | None = None

    if not folder.is_dir():
        errors.append(ValidationIssue(str(folder), None, "Folder not found"))
        return FolderPreview(None, None, None, stories, errors)

    epic_path = folder / "epic.md"
    epic_content = _read_file(epic_path, errors)
    if epic_content is not None:
        epic_hash = hashlib.sha256(epic_content.encode("utf-8")).hexdigest()
        heading = _EPIC_HEADING.search(epic_content)
        if heading is None:
            errors.append(ValidationIssue("epic.md", 1, "Expected '# Epic: <title>' heading"))
        else:
            epic_title = heading.group(1).strip()
        error_count = len(errors)
        _validate_fields(epic_content, "epic.md", 1, errors)
        if heading is not None and len(errors) == error_count:
            try:
                epic = _parse_epic_content(epic_content)
            except (BusinessRuleViolation, ValueError) as error:
                errors.append(ValidationIssue("epic.md", None, str(error)))

    stories_path = folder / "stories.md"
    if stories_path.exists():
        stories_content = _read_file(stories_path, errors)
        if stories_content is not None:
            markers = list(_STORY_MARKER.finditer(stories_content))
            preamble = stories_content[:markers[0].start()] if markers else stories_content
            for line_number, line in enumerate(preamble.splitlines(), start=1):
                if line.strip() and not re.fullmatch(
                    r"(?:# Stories for Epic:.*|---)", line.strip()
                ):
                    errors.append(ValidationIssue(
                        "stories.md", line_number, "Expected '### <id>: <title>' story heading"
                    ))
            if markers:
                for heading in _WRONG_LEVEL_HEADING.finditer(stories_content[markers[0].start():]):
                    line_number = stories_content.count("\n", 0, markers[0].start() + heading.start()) + 1
                    errors.append(ValidationIssue(
                        "stories.md", line_number, "Expected '### <id>: <title>' story heading"
                    ))
            story_ids: set[str] = set()
            for index, marker in enumerate(markers):
                line_number = stories_content.count("\n", 0, marker.start()) + 1
                block_end = markers[index + 1].start() if index + 1 < len(markers) else len(stories_content)
                block = stories_content[marker.start():block_end]
                error_count = len(errors)
                _validate_fields(block, "stories.md", line_number, errors)
                heading = _STORY_HEADING.fullmatch(marker.group())
                if heading is None:
                    errors.append(ValidationIssue("stories.md", line_number, "Expected '### <id>: <title>' heading"))
                    continue
                story_id = heading.group(1).strip()
                title = heading.group(2).strip()
                if story_id == "epic":
                    errors.append(ValidationIssue(
                        "stories.md", line_number, "Story ID 'epic' is reserved"
                    ))
                if story_id in story_ids:
                    errors.append(ValidationIssue(
                        "stories.md", line_number, f"Duplicate story ID: {story_id}"
                    ))
                story_ids.add(story_id)
                story: UserStory | None = None
                if len(errors) == error_count:
                    try:
                        story = _parse_story_block(title, block)
                    except (BusinessRuleViolation, ValueError) as error:
                        errors.append(ValidationIssue("stories.md", line_number, str(error)))
                source_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
                stories.append(StoryPreview(story_id, title, line_number, story, source_hash))

    return FolderPreview(epic_title, epic, epic_hash, stories, errors)
