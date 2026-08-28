import os
from pathlib import Path
from typing import Optional

import typer
from InquirerPy import inquirer

from devworkwire.composition.container import Composition, build_composition
from devworkwire.config.app_config import AppConfig
from devworkwire.config.project_config import ProjectConfig
from devworkwire.features.epic.presentation.commands import create_epic, fetch_epic
from devworkwire.features.work_items.presentation.commands import (
    import_commit,
    import_preview,
    import_status,
)
from devworkwire.infrastructure.external.jira.settings import JiraSettings

# Initialize Typer app with help when no command is provided
app = typer.Typer(no_args_is_help=False)
import_app = typer.Typer(help="Import work structures from markdown files.")
app.add_typer(import_app, name="import")

_composition: Composition | None = None
_config_path: Path | None = None


def _build_composition() -> Composition:
    """Build the composition root from current config."""
    jira_config = AppConfig.instance().get_config("jira")
    settings = JiraSettings.from_dict(jira_config)
    project_config = ProjectConfig.load(_config_path)
    return build_composition(settings, project_config)


def get_composition() -> Composition:
    """Lazily build the composition root on first access."""
    global _composition  # noqa: PLW0603
    if _composition is None:
        _composition = _build_composition()
    return _composition


def show_welcome_message():
    """Display the welcome message."""
    typer.echo("╭──────────────────────────────────────────────────────────────╮")
    typer.echo("│                                                              │")
    typer.echo("│        ⚡ DevWorkWire                                        │")
    typer.echo("│        Backlog loading, validated and duplicate-free         │")
    typer.echo("│                                                              │")
    typer.echo("╰──────────────────────────────────────────────────────────────╯")
    typer.echo("")
    typer.echo("System ready.")
    typer.echo("")


@app.command("fetch-epic")
def fetch_epic_command(
    issue_id: str = typer.Argument(..., help="Jira issue key, e.g. PROJ-123"),
):
    """Fetch an epic and its stories from Jira by key."""
    fetch_epic(get_composition(), issue_id)


@app.command("create-epic")
def create_epic_command(
    file_path: str = typer.Argument(..., help="Path to the epic markdown file"),
):
    """Create a new epic in Jira from a markdown file."""
    create_epic(get_composition(), file_path)


@import_app.command("preview")
def import_preview_command(
    file_path: str = typer.Argument(..., help="Path to the epic markdown file"),
):
    """Parse and validate a markdown file, then save a preview."""
    import_preview(file_path)


@import_app.command("commit")
def import_commit_command(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Execute the import using the last saved preview."""
    import_commit(confirm=yes)


@import_app.command("status")
def import_status_command():
    """Show all completed imports."""
    import_status()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Path to devworkwire.yml (default: ./devworkwire.yml)",
    ),
):
    """DevWorkWire: load validated work structures into your project tracker.

    Runs the interactive menu when no command is provided.
    """
    global _config_path  # noqa: PLW0603
    _config_path = Path(config) if config else None
    if ctx.invoked_subcommand is None:
        show_welcome_message()
        interactive_menu(skip_initial_prompt=False)


def interactive_menu(skip_initial_prompt=False):
    """Handles the interactive user menu."""
    while True:
        if not skip_initial_prompt:
            skip_initial_prompt = True
        else:
            typer.echo("\nPress Enter to go back to the main menu...")
            input()
        os.system("cls" if os.name == "nt" else "clear")
        show_welcome_message()
        menu_options = {
            "get_epic": "Retrieve an epic and its stories by JIRA key",
            "create_epic": "Create a new epic in JIRA from file",
            "exit": "Exit the application",
        }
        menu_choice = inquirer.select(
            message="Select an option:",
            choices=[
                {"name": description, "value": key}
                for key, description in menu_options.items()
            ],
        ).execute()

        if menu_choice == "get_epic":
            jira_key = inquirer.text(message="Enter the JIRA key:").execute()
            fetch_epic(get_composition(), jira_key)
        elif menu_choice == "create_epic":
            file_path = inquirer.text(
                message="Enter the path to the Epic file:"
            ).execute()
            if not file_path:
                file_path = "data/EPIC-0-foundational/epic-0.md"

            create_epic(get_composition(), file_path)
        elif menu_choice == "exit":
            typer.echo("Thanks for using DevWorkWire! Have a great day!")
            break


if __name__ == "__main__":
    app()
