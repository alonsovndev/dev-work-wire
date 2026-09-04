import asyncio
import typer
from devworkwire.core.composition import Container
from devworkwire.features.import_.application.markdown_parser import parse_epic_markdown

app = typer.Typer(no_args_is_help=True)
container = Container()

@app.command()
def fetch_epic(key: str):
    """Fetch an epic from Jira."""
    async def _run():
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

    asyncio.run(_run())

@app.command()
def create_epic(path: str):
    """Create an epic in Jira from a markdown file."""
    async def _run():
        try:
            epic = parse_epic_markdown(path)
            provider = container.get_jira_provider()
            issue_key = await provider.create_epic(epic)
            typer.echo(f"Successfully created epic: {issue_key}")
        except Exception as e:
            typer.echo(f"Error creating epic: {e}", err=True)

    asyncio.run(_run())

if __name__ == "__main__":
    app()
