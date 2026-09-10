import asyncio
import os
import sys

import typer
from InquirerPy import inquirer

from devworkwire.core.composition import Container
from devworkwire.features.import_.application.markdown_parser import (
    parse_epic_markdown,
    parse_stories_markdown,
)
from devworkwire.presentation.cli.banner import print_banner
from devworkwire.presentation.cli.epic_panel import render_epic_panel

app = typer.Typer()
container = Container()

_RETRIEVE_EPIC = "Retrieve an epic from Jira by key"
_CREATE_EPIC = "Load an epic and its stories from a folder and upload to JIRA"
_EXIT = "Exit"

_EPIC_FILENAME = "epic.md"
_STORIES_FILENAME = "stories.md"


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """DevWorkWire CLI. Run without a subcommand for the interactive menu."""
    if ctx.invoked_subcommand is None:
        _run_interactive_menu()


@app.command("fetch-epic")
def fetch_epic(key: str) -> None:
    """Fetch an epic from Jira."""
    asyncio.run(_fetch_epic(key))


@app.command("create-epic")
def create_epic(folder_path: str) -> None:
    """Create an epic and its stories in Jira from a folder containing epic.md and stories.md."""
    asyncio.run(_create_epic(folder_path))


async def _fetch_epic(key: str) -> None:
    try:
        provider = container.get_jira_provider()
        epic = await provider.fetch_epic(key)
        if epic:
            typer.secho(render_epic_panel(epic), fg=typer.colors.CYAN)
        else:
            typer.echo(f"Epic {key} not found.")
    except Exception as e:
        typer.echo(f"Error fetching epic: {e}", err=True)


async def _create_epic(folder_path: str) -> None:
    try:
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"Folder not found: {folder_path}")

        epic = parse_epic_markdown(os.path.join(folder_path, _EPIC_FILENAME))
        provider = container.get_jira_provider()
        issue_key = await provider.create_epic(epic)
        typer.echo(f"Successfully created epic: {issue_key}")
    except Exception as e:
        typer.echo(f"Error creating epic: {e}", err=True)
        return

    stories = parse_stories_markdown(os.path.join(folder_path, _STORIES_FILENAME))
    for story in stories:
        try:
            story_key = await provider.create_story(story, epic_key=issue_key)
            typer.echo(f"Successfully created story: {story_key} ({story.title})")
        except Exception as e:
            typer.echo(f"Error creating story '{story.title}': {e}", err=True)


def _clear_screen() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[1;1H")
        sys.stdout.flush()


def _run_interactive_menu() -> None:
    """Keyboard-navigable main menu, shown when `dwire` is run with no subcommand."""
    while True:
        _clear_screen()
        print_banner()
        choice = inquirer.select(
            message="Choose an action:",
            choices=[_RETRIEVE_EPIC, _CREATE_EPIC, _EXIT],
        ).execute()

        if choice == _EXIT:
            break
        if choice == _RETRIEVE_EPIC:
            key = inquirer.text(message="Jira issue key (e.g. PROJ-123):").execute()
            asyncio.run(_fetch_epic(key))
            inquirer.confirm(
                message="Press Enter to return to the menu...", default=True
            ).execute()
        elif choice == _CREATE_EPIC:
            folder_path = inquirer.text(
                message="Enter the path to the folder containing epic.md and stories.md:"
            ).execute()
            asyncio.run(_create_epic(folder_path))
            inquirer.confirm(
                message="Press Enter to return to the menu...", default=True
            ).execute()


if __name__ == "__main__":
    app()
