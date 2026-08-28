"""CLI command handlers for the epic feature.

These functions are the presentation-layer entry points for epic flows.
They receive a pre-built Container from the composition root, keeping the
adapter choice fully behind the presentation boundary.
"""

import asyncio

import typer

from devworkwire.composition.container import Composition
from devworkwire.core.domain.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)
from devworkwire.features.epic.application.use_cases import (
    CreateEpicFromMarkdown,
    GetEpicWithStories,
)


def fetch_epic(composition: Composition, issue_id: str):
    """
    Fetch an epic and its stories from JIRA using the epic key.

    Args:
        composition: Pre-built composition root holding repository ports.
        issue_id: The key of the epic to retrieve (e.g. "PROJ-123").
    """

    async def main():
        use_case = GetEpicWithStories(provider=composition.work_item_provider)
        try:
            dto = await use_case.execute(issue_id)
            typer.echo("Epic Summary:")
            typer.echo(f"Key: {dto.key}")
            typer.echo(f"Summary: {dto.summary}")
            typer.echo(f"Description: {dto.description}")
            typer.echo("")
            typer.echo(f"Stories ({len(dto.user_stories)}):")
            for story in dto.user_stories:
                status = f" [{story.status}]" if story.status else ""
                typer.echo(f"  - {story.key}: {story.summary}{status}")
        except EntityNotFoundException:
            typer.echo(f"Epic not found: {issue_id}")
        except BusinessRuleViolationException as e:
            typer.echo(f"Error fetching epic: {e}")
        except Exception as e:  # keep interactive session alive on unexpected errors
            typer.echo(f"Unexpected error fetching epic: {e}")

    # Use asyncio.run to handle the async call
    asyncio.run(main())


def create_epic(composition: Composition, file_path: str):
    """
    Create a new epic in JIRA from an Epic markdown file.

    Args:
        composition: Pre-built composition root holding repository ports.
        file_path: Path to the markdown file describing the epic.
    """

    async def main():
        use_case = CreateEpicFromMarkdown(provider=composition.work_item_provider)

        try:
            with open(file_path, "r") as file:
                markdown_content = file.read()
        except OSError as e:
            # OSError covers missing, unreadable, and directory paths.
            typer.echo(f"Cannot read file. Error: {e}")
            return

        try:
            dto = await use_case.execute(markdown_content)
        except BusinessRuleViolationException as e:
            typer.echo(f"Invalid file or content. Error: {e}")
            return

        typer.echo("Epic Successfully Created!")
        typer.echo(f"Key: {dto.key}")
        typer.echo(f"Summary: {dto.summary}")
        typer.echo(f"Description: {dto.description}")

    # Use asyncio.run to handle the async call
    asyncio.run(main())
