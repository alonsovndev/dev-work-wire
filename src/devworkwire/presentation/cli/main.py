import asyncio

import typer
from InquirerPy import inquirer

from devworkwire.core.composition import Container
from devworkwire.features.import_.application.markdown_parser import parse_epic_markdown
from devworkwire.presentation.cli.banner import print_banner

app = typer.Typer()
container = Container()

_RETRIEVE_EPIC = "Retrieve an epic from Jira by key"
_CREATE_EPIC = "Create a new epic in Jira from a markdown file"
_EXIT = "Exit"


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
def create_epic(path: str) -> None:
    """Create an epic in Jira from a markdown file."""
    asyncio.run(_create_epic(path))


async def _fetch_epic(key: str) -> None:
    try:
        provider = container.get_jira_provider()
        epic = await provider.fetch_epic(key)
        if epic:
            typer.echo(f"Epic Found: {epic.title}")
            typer.echo(f"Description: {epic.description}")
        else:
            typer.echo(f"Epic {key} not found.")
    except Exception as e:
        typer.echo(f"Error fetching epic: {e}", err=True)


async def _create_epic(path: str) -> None:
    try:
        epic = parse_epic_markdown(path)
        provider = container.get_jira_provider()
        issue_key = await provider.create_epic(epic)
        typer.echo(f"Successfully created epic: {issue_key}")
    except Exception as e:
        typer.echo(f"Error creating epic: {e}", err=True)


def _run_interactive_menu() -> None:
    """Keyboard-navigable main menu, shown when `dwire` is run with no subcommand."""
    print_banner()
    while True:
        choice = inquirer.select(
            message="Choose an action:",
            choices=[_RETRIEVE_EPIC, _CREATE_EPIC, _EXIT],
        ).execute()

        if choice == _EXIT:
            break
        if choice == _RETRIEVE_EPIC:
            key = inquirer.text(message="Jira issue key (e.g. PROJ-123):").execute()
            asyncio.run(_fetch_epic(key))
        elif choice == _CREATE_EPIC:
            path = inquirer.filepath(message="Path to epic markdown file:").execute()
            asyncio.run(_create_epic(path))


if __name__ == "__main__":
    app()
