import asyncio
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
import typer
from InquirerPy import inquirer

from devworkwire.core.composition import Container
from devworkwire.core.domain import Epic, Label, Priority, StoryPoints, UserStory
from devworkwire.features.import_.application.folder_preview import (
    FolderPreview,
    preview_folder as load_folder_preview,
)
from devworkwire.features.import_.application.folder_state import (
    ImportState,
    ItemRecord,
    lock_folder,
)
from devworkwire.presentation.cli.banner import print_banner
from devworkwire.presentation.cli.epic_panel import render_epic_panel, render_story_panel

app = typer.Typer()
container = Container()

_FETCH_EPIC = "Retrieve an epic from Jira by key"
_FETCH_STORY = "Retrieve a story from Jira by key"
_LIST_STORIES = "List stories in an epic"
_LIST_ASSIGNED = "List open work assigned to a user"
_CREATE_EPIC = "Create one epic in Jira"
_CREATE_STORY = "Create one story in an existing epic"
_PREVIEW_FOLDER = "Preview and validate a folder"
_IMPORT_FOLDER = "Import an epic and its stories from a folder"
_EXIT = "Exit"


@dataclass(frozen=True)
class WorkItemInput:
    title: str
    description: str = ""
    priority: str | None = None
    labels: tuple[str, ...] = ()
    points: int | None = None


def _priority(value: str | None) -> Priority | None:
    return Priority.from_jira_name(value.strip()) if value and value.strip() else None


def _labels(values: tuple[str, ...]) -> list[Label]:
    return [Label(name=value.strip()) for value in values]


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """DevWorkWire CLI. Run without a subcommand for the interactive menu."""
    if ctx.invoked_subcommand is None:
        _run_interactive_menu()


@app.command("fetch-epic")
def fetch_epic(key: str) -> None:
    if not asyncio.run(_fetch_epic(key)):
        raise typer.Exit(code=1)


@app.command("fetch-story")
def fetch_story(key: str) -> None:
    if not asyncio.run(_fetch_story(key)):
        raise typer.Exit(code=1)


@app.command("list-stories")
def list_stories(epic_key: str) -> None:
    if not asyncio.run(_list_stories(epic_key)):
        raise typer.Exit(code=1)


@app.command("list-assigned")
def list_assigned(
    assignee: Optional[str] = typer.Option(None, "--assignee")
) -> None:
    """List open work assigned to the current user or a Jira account ID."""
    if not asyncio.run(_list_assigned(assignee)):
        raise typer.Exit(code=1)


@app.command("create-epic")
def create_epic(
    title: str = typer.Option(..., "--title"),
    description: str = typer.Option("", "--description"),
    priority: Optional[str] = typer.Option(None, "--priority"),
    labels: list[str] = typer.Option([], "--label"),
) -> None:
    """Create one epic. Repeat --label to add multiple labels."""
    item = WorkItemInput(title, description, priority, tuple(labels))
    if not asyncio.run(_create_epic(item)):
        raise typer.Exit(code=1)


@app.command("create-story")
def create_story(
    epic_key: str,
    title: str = typer.Option(..., "--title"),
    description: str = typer.Option("", "--description"),
    priority: Optional[str] = typer.Option(None, "--priority"),
    labels: list[str] = typer.Option([], "--label"),
    points: Optional[int] = typer.Option(None, "--points", min=0),
) -> None:
    """Create one story under an existing epic."""
    item = WorkItemInput(title, description, priority, tuple(labels), points)
    if not asyncio.run(_create_story(epic_key, item)):
        raise typer.Exit(code=1)


@app.command("import-folder")
def import_folder(
    folder_path: str,
    yes: bool = typer.Option(False, "--yes", help="Create without an interactive confirmation"),
) -> None:
    """Upload epic.md and optional stories.md from a folder."""
    if not asyncio.run(_import_folder(folder_path, yes=yes)):
        raise typer.Exit(code=1)


@app.command("preview-folder")
def preview_folder(folder_path: str) -> None:
    """Show local work items and validation errors without contacting Jira."""
    if not _preview_folder(folder_path):
        raise typer.Exit(code=1)


@app.command("resolve-import")
def resolve_import(
    folder_path: str,
    item: str = typer.Option(..., "--item", help="epic or a story ID"),
    key: Optional[str] = typer.Option(None, "--key", help="Existing Jira issue key"),
    retry: bool = typer.Option(False, "--retry", help="Clear a confirmed absent attempt"),
) -> None:
    """Resolve an uncertain import after checking Jira."""
    if (key is None and not retry) or (key is not None and retry):
        typer.echo("Choose exactly one of --key or --retry.", err=True)
        raise typer.Exit(code=1)
    if not asyncio.run(_resolve_import(folder_path, item, key, retry)):
        raise typer.Exit(code=1)


@app.command("rebind-import-story")
def rebind_import_story(folder_path: str, old_id: str, new_id: str) -> None:
    """Keep a recorded Jira key when a story heading ID changes."""
    if not _reconcile_missing_story(folder_path, old_id, new_id):
        raise typer.Exit(code=1)


@app.command("retire-import-story")
def retire_import_story(folder_path: str, story_id: str) -> None:
    """Remove a recorded story that is no longer in stories.md."""
    if not _reconcile_missing_story(folder_path, story_id, None):
        raise typer.Exit(code=1)


async def _fetch_epic(key: str) -> bool:
    try:
        epic = await container.get_jira_provider().fetch_epic(key)
        if epic is None:
            typer.echo(f"Epic {key} not found.", err=True)
            return False
        typer.secho(render_epic_panel(epic), fg=typer.colors.CYAN)
        return True
    except Exception as error:
        typer.echo(f"Error fetching epic: {error}", err=True)
        return False


async def _fetch_story(key: str) -> bool:
    try:
        story = await container.get_jira_provider().fetch_story(key)
        if story is None:
            typer.echo(f"Story {key} not found.", err=True)
            return False
        typer.secho(render_story_panel(story), fg=typer.colors.CYAN)
        return True
    except Exception as error:
        typer.echo(f"Error fetching story: {error}", err=True)
        return False


async def _list_stories(epic_key: str) -> bool:
    try:
        provider = container.get_jira_provider()
        if await provider.fetch_epic(epic_key) is None:
            typer.echo(f"Epic {epic_key} not found.", err=True)
            return False
        stories = await provider.list_stories(epic_key)
        if not stories:
            typer.echo(f"No stories found in epic {epic_key}.")
            return True
        for story in stories:
            key = story.issue_id.key if story.issue_id else "Unknown"
            typer.echo(f"{key}  {story.title}  [{story.status or 'Unknown'}]")
        return True
    except Exception as error:
        typer.echo(f"Error listing stories: {error}", err=True)
        return False


async def _list_assigned(account_id: str | None) -> bool:
    try:
        work_items = await container.get_jira_provider().list_assigned_work_items(account_id)
        if not work_items:
            typer.echo("No open work items assigned to this user in the configured project.")
            return True
        for work_item in work_items:
            typer.echo(
                f"{work_item.key}  {work_item.issue_type}  "
                f"{work_item.title}  [{work_item.status}]"
            )
        return True
    except Exception as error:
        typer.echo(f"Error listing assigned work: {error}", err=True)
        return False


async def _create_epic(item: WorkItemInput) -> bool:
    try:
        epic = Epic.create(
            title=item.title,
            description=item.description,
            priority=_priority(item.priority),
            labels=_labels(item.labels),
        )
        issue_key = await container.get_jira_provider().create_epic(epic)
        typer.echo(f"Successfully created epic: {issue_key}")
        return True
    except Exception as error:
        typer.echo(f"Error creating epic: {error}", err=True)
        return False


async def _create_story(epic_key: str, item: WorkItemInput) -> bool:
    try:
        story = UserStory.create(
            title=item.title,
            description=item.description,
            priority=_priority(item.priority),
            story_points=StoryPoints(value=item.points) if item.points is not None else None,
            labels=_labels(item.labels),
        )
        provider = container.get_jira_provider()
        if await provider.fetch_epic(epic_key) is None:
            typer.echo(f"Epic {epic_key} not found.", err=True)
            return False
        issue_key = await provider.create_story(story, epic_key=epic_key)
        typer.echo(f"Successfully created story: {issue_key}")
        return True
    except Exception as error:
        typer.echo(f"Error creating story: {error}", err=True)
        return False


def _show_folder_preview(preview: FolderPreview, state: ImportState | None = None) -> None:
    typer.echo(f"Epic: {preview.epic_title or '(missing or invalid)'}")
    if state is not None:
        _show_item_status("epic", state.epic, preview.epic_hash)
    if preview.epic is not None:
        epic_details = []
        if preview.epic.priority:
            epic_details.append(f"priority={preview.epic.priority.name}")
        if preview.epic.labels:
            epic_details.append(f"labels={', '.join(label.name for label in preview.epic.labels)}")
        if epic_details:
            typer.echo(f"  {', '.join(epic_details)}")
    typer.echo(f"Stories ({len(preview.stories)}):")
    for story in preview.stories:
        details = []
        if story.item is not None:
            if story.item.priority:
                details.append(f"priority={story.item.priority.name}")
            if story.item.labels:
                details.append(f"labels={', '.join(label.name for label in story.item.labels)}")
            if story.item.story_points is not None:
                details.append(f"points={story.item.story_points.value}")
        suffix = f" — {', '.join(details)}" if details else ""
        typer.echo(f"  - {story.title} (stories.md:{story.line}){suffix}")
        if state is not None:
            _show_item_status(story.story_id, state.stories.get(story.story_id), story.source_hash)
    if state is not None:
        missing_ids = _missing_story_ids(preview, state)
        if missing_ids:
            typer.echo("Recorded stories missing from stories.md:", err=True)
            for story_id in sorted(missing_ids):
                record = state.stories[story_id]
                detail = record.key or "unresolved attempt"
                typer.echo(f"  - {story_id}: {detail}", err=True)
    if preview.errors:
        typer.echo(f"Errors ({len(preview.errors)}):", err=True)
        for error in preview.errors:
            typer.echo(f"  - {error}", err=True)


def _show_item_status(item: str, record: ItemRecord | None, source_hash: str | None) -> None:
    if record is None:
        typer.echo(f"    {item}: to create")
    elif record.status == "pending":
        typer.echo(f"    {item}: unresolved attempt; resolve before importing", err=True)
    else:
        typer.echo(f"    {item}: already uploaded as {record.key}; will skip")
    if record is not None and source_hash is not None and record.source_hash != source_hash:
        typer.echo(f"    {item}: Markdown changed since recorded attempt; Jira will not be updated", err=True)


def _has_pending(state: ImportState) -> bool:
    return state.epic is not None and state.epic.status == "pending" or any(
        record.status == "pending" for record in state.stories.values()
    )


def _missing_story_ids(preview: FolderPreview, state: ImportState) -> set[str]:
    return set(state.stories) - {story.story_id for story in preview.stories}


def _definitely_rejected(error: Exception) -> bool:
    return (
        isinstance(error, httpx.HTTPStatusError)
        and 400 <= error.response.status_code < 500
        and error.response.status_code not in (408, 429)
    )


def _preview_folder(folder_path: str) -> bool:
    preview = load_folder_preview(folder_path)
    try:
        state = ImportState.load(Path(folder_path)) if Path(folder_path).is_dir() else None
    except ValueError as error:
        _show_folder_preview(preview)
        typer.echo(str(error), err=True)
        return False
    _show_folder_preview(preview, state)
    if state is not None and state.base_url is None:
        typer.echo("No resume record; existing Jira items cannot be identified locally.")
    return not preview.errors and (
        state is None or not _has_pending(state) and not _missing_story_ids(preview, state)
    )


async def _import_folder(folder_path: str, yes: bool = False) -> bool:
    try:
        folder = Path(folder_path)
        if not folder.is_dir():
            _show_folder_preview(load_folder_preview(folder_path))
            return False
        with lock_folder(folder):
            return await _import_locked(folder, yes)
    except (OSError, ValueError) as error:
        typer.echo(f"Error importing folder: {error}", err=True)
        return False


async def _import_locked(folder: Path, yes: bool) -> bool:
    preview = load_folder_preview(str(folder))
    try:
        state = ImportState.load(folder)
    except ValueError as error:
        _show_folder_preview(preview)
        typer.echo(str(error), err=True)
        return False
    _show_folder_preview(preview, state)
    if preview.errors or _has_pending(state):
        return False
    if _missing_story_ids(preview, state):
        typer.echo(
            "Rebind or retire missing story IDs before importing new items.", err=True
        )
        return False
    if state.base_url is None:
        typer.echo("No resume record; existing Jira items cannot be identified locally.")
    provider = None
    if state.base_url is not None:
        try:
            provider = container.get_jira_provider()
            state.require_destination(provider.settings.base_url, provider.settings.project_key)
        except Exception as error:
            typer.echo(f"Error importing folder: {error}", err=True)
            return False
    if state.epic is not None and all(
        story.story_id in state.stories for story in preview.stories
    ):
        typer.echo("All work items are already uploaded.")
        return True
    if not yes:
        if not sys.stdin.isatty():
            typer.echo("Use --yes to create items without an interactive terminal.", err=True)
            return False
        if not typer.confirm("Create these work items in Jira?", default=False):
            typer.echo("Import cancelled; no work items were created.")
            return True

    if provider is None:
        try:
            provider = container.get_jira_provider()
            state.require_destination(provider.settings.base_url, provider.settings.project_key)
        except Exception as error:
            typer.echo(f"Error importing folder: {error}", err=True)
            return False

    assert preview.epic is not None and preview.epic_hash is not None
    if state.epic is None:
        state.epic = ItemRecord("pending", preview.epic_hash)
        try:
            state.save()
            issue_key = await provider.create_epic(preview.epic)
            state.epic = ItemRecord("created", preview.epic_hash, issue_key)
            state.save()
            typer.echo(f"Successfully created epic: {issue_key}")
        except Exception as error:
            if _definitely_rejected(error):
                state.epic = None
                state.save()
            typer.echo(f"Error importing folder: {error}", err=True)
            return False

    assert state.epic.key is not None
    all_created = True
    for story_preview in preview.stories:
        if story_preview.story_id in state.stories:
            continue
        assert story_preview.item is not None
        state.stories[story_preview.story_id] = ItemRecord("pending", story_preview.source_hash)
        try:
            state.save()
            story_key = await provider.create_story(story_preview.item, epic_key=state.epic.key)
            state.stories[story_preview.story_id] = ItemRecord(
                "created", story_preview.source_hash, story_key
            )
            state.save()
            typer.echo(f"Successfully created story: {story_key} ({story_preview.title})")
        except Exception as error:
            typer.echo(f"Error creating story '{story_preview.title}': {error}", err=True)
            if _definitely_rejected(error):
                del state.stories[story_preview.story_id]
                try:
                    state.save()
                except OSError as save_error:
                    typer.echo(f"Cannot save import state: {save_error}", err=True)
                    return False
                all_created = False
                continue
            typer.echo("Uncertain Jira outcome; resolve this item before retrying.", err=True)
            return False
    return all_created


async def _resolve_import(folder_path: str, item: str, key: str | None, retry: bool) -> bool:
    try:
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Folder not found: {folder}")
        with lock_folder(folder):
            state = ImportState.load(folder)
            record = state.epic if item == "epic" else state.stories.get(item)
            if record is None or record.status != "pending":
                raise ValueError(f"No unresolved attempt for {item}")
            provider = container.get_jira_provider()
            state.require_destination(provider.settings.base_url, provider.settings.project_key)
            if key is not None:
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*-\d+", key) or not key.startswith(
                    f"{state.project_key}-"
                ):
                    raise ValueError(f"Jira key must belong to project {state.project_key}")
                if item == "epic":
                    if await provider.fetch_epic(key) is None:
                        raise ValueError(f"Jira issue {key} was not found")
                else:
                    story = await provider.fetch_story(key)
                    if story is None:
                        raise ValueError(f"Jira issue {key} was not found")
                    if state.epic is None or story.epic_key != state.epic.key:
                        raise ValueError(f"Story {key} is not linked to the recorded epic")
                resolved = ItemRecord("created", record.source_hash, key)
            if retry:
                if item == "epic":
                    state.epic = None
                else:
                    del state.stories[item]
            else:
                if item == "epic":
                    state.epic = resolved
                else:
                    state.stories[item] = resolved
            state.save()
        typer.echo(f"Resolved {item}: {'ready to retry' if retry else key}")
        return True
    except Exception as error:
        typer.echo(f"Error resolving import: {error}", err=True)
        return False


def _reconcile_missing_story(folder_path: str, old_id: str, new_id: str | None) -> bool:
    try:
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Folder not found: {folder}")
        with lock_folder(folder):
            preview = load_folder_preview(str(folder))
            if preview.errors:
                raise ValueError("Fix folder validation errors before reconciling stories")
            state = ImportState.load(folder)
            current_ids = {story.story_id for story in preview.stories}
            record = state.stories.get(old_id)
            if record is None or record.status != "created" or old_id in current_ids:
                raise ValueError(f"{old_id} is not a missing uploaded story")
            if new_id is not None:
                if new_id not in current_ids or new_id in state.stories:
                    raise ValueError(f"{new_id} must be a new story ID in stories.md")
                state.stories[new_id] = record
            del state.stories[old_id]
            state.save()
        action = f"rebound to {new_id}" if new_id is not None else "retired"
        typer.echo(f"Story {old_id} {action}.")
        return True
    except Exception as error:
        typer.echo(f"Error reconciling import: {error}", err=True)
        return False


def _clear_screen() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[1;1H")
        sys.stdout.flush()


def _prompt_item(include_points: bool = False) -> WorkItemInput:
    title = inquirer.text(message="Title:").execute()
    description = inquirer.text(message="Description (optional):").execute()
    priority = inquirer.text(message="Priority (optional):").execute()
    labels_text = inquirer.text(message="Labels, comma-separated (optional):").execute()
    labels = tuple(label.strip() for label in labels_text.split(",") if label.strip())
    points = None
    if include_points:
        points_text = inquirer.text(message="Story points, whole number (optional):").execute()
        if points_text.strip():
            points = int(points_text)
            if points < 0:
                raise ValueError("Story points cannot be negative")
    return WorkItemInput(title, description, priority, labels, points)


def _run_interactive_menu() -> None:
    """Keyboard-navigable main menu, shown when `dwire` has no subcommand."""
    while True:
        _clear_screen()
        print_banner()
        choice = inquirer.select(
            message="Choose an action:",
            choices=[
                _FETCH_EPIC, _FETCH_STORY, _LIST_STORIES, _LIST_ASSIGNED, _CREATE_EPIC,
                _CREATE_STORY, _PREVIEW_FOLDER, _IMPORT_FOLDER, _EXIT,
            ],
        ).execute()

        if choice == _EXIT:
            break
        try:
            if choice == _FETCH_EPIC:
                key = inquirer.text(message="Jira epic key (e.g. PROJ-123):").execute()
                asyncio.run(_fetch_epic(key))
            elif choice == _FETCH_STORY:
                key = inquirer.text(message="Jira story key (e.g. PROJ-124):").execute()
                asyncio.run(_fetch_story(key))
            elif choice == _LIST_STORIES:
                key = inquirer.text(message="Jira epic key (e.g. PROJ-123):").execute()
                asyncio.run(_list_stories(key))
            elif choice == _LIST_ASSIGNED:
                account_id = inquirer.text(
                    message="Jira account ID (leave blank for current user):"
                ).execute().strip()
                asyncio.run(_list_assigned(account_id or None))
            elif choice == _CREATE_EPIC:
                asyncio.run(_create_epic(_prompt_item()))
            elif choice == _CREATE_STORY:
                key = inquirer.text(message="Parent epic key (e.g. PROJ-123):").execute()
                asyncio.run(_create_story(key, _prompt_item(include_points=True)))
            elif choice == _PREVIEW_FOLDER:
                folder_path = inquirer.text(
                    message="Folder containing epic.md and optional stories.md:"
                ).execute()
                _preview_folder(folder_path)
            elif choice == _IMPORT_FOLDER:
                folder_path = inquirer.text(
                    message="Folder containing epic.md and optional stories.md:"
                ).execute()
                asyncio.run(_import_folder(folder_path))
        except ValueError as error:
            typer.echo(f"Invalid input: {error}", err=True)
        inquirer.confirm(
            message="Press Enter to return to the menu...", default=True
        ).execute()


if __name__ == "__main__":
    app()
