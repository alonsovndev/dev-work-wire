"""CLI commands for the import feature."""

from __future__ import annotations

import asyncio

import typer


def _run(coro):
    """Run an async coroutine from a sync CLI command."""
    return asyncio.run(coro)


def _get_import_service():
    from devworkwire.composition.container import get_import_service

    return get_import_service()


def import_preview(file_path: str) -> None:
    """Parse and validate a markdown file, then save a preview."""
    svc = _get_import_service()
    try:
        result = _run(svc.preview(file_path))
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("")
    typer.echo("═══ Import Preview ═════════════════════════════════════════")
    typer.echo(f"  Source : {result.source_path}")
    typer.echo(f"  Hash   : {result.source_hash}")
    typer.echo("")
    typer.echo(f"  Epic   : {result.epic.key} — {result.epic.title}")
    if result.epic.description:
        desc_preview = result.epic.description[:120]
        if len(result.epic.description) > 120:
            desc_preview += "..."
        typer.echo(f"  Desc   : {desc_preview}")
    typer.echo(f"  Stories: {len(result.epic.stories)}")
    typer.echo("")

    for i, story in enumerate(result.epic.stories, 1):
        typer.echo(f"  [{i}] {story.key} — {story.title}")
        if story.acceptance_criteria:
            for ac in story.acceptance_criteria:
                typer.echo(f"      • {ac}")

    typer.echo("")
    if result.validation.is_valid:
        typer.echo("  ✓ Validation passed")
        if result.validation.warnings:
            for w in result.validation.warnings:
                typer.echo(f"  ⚠ {w}")
        typer.echo("")
        typer.echo("  Run 'dwire import commit' to execute the import.")
    else:
        typer.echo("  ✗ Validation failed:")
        for e in result.validation.errors:
            typer.echo(f"    — {e}")
        typer.echo("")
        typer.echo("  Fix the markdown file and run preview again.")
        raise typer.Exit(1)


def import_commit(confirm: bool = False) -> None:
    """Execute the import using the last saved preview."""
    svc = _get_import_service()

    if not confirm:
        if not typer.confirm("Proceed with import?"):
            typer.echo("Aborted.")
            raise typer.Exit(0)

    try:
        result = _run(svc.commit())
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("")
    typer.echo("═══ Import Complete ════════════════════════════════════════")
    typer.echo(f"  Epic: {result.epic_key}")
    typer.echo("")

    for item in result.items:
        status = "✓" if item.action == "created" else "○"
        typer.echo(
            f"  {status} {item.item_type:6s} {item.item_key} → {item.provider_key}"
        )

    created = sum(1 for i in result.items if i.action == "created")
    skipped = sum(1 for i in result.items if i.action == "skipped")
    typer.echo("")
    typer.echo(f"  Created: {created}  Skipped: {skipped}")
    typer.echo("")


def import_status() -> None:
    """Show all completed imports."""
    svc = _get_import_service()
    records = svc.status()

    if not records:
        typer.echo("No imports recorded yet.")
        return

    typer.echo("")
    typer.echo("═══ Import History ═════════════════════════════════════════")
    typer.echo("")

    for record in records:
        typer.echo(f"  {record.epic.key:12s}  {record.source_path}")
        typer.echo(f"  {'':12s}  imported at {record.created_at.isoformat()}")

    typer.echo("")
