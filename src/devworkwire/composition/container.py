"""Composition root: wires ports to concrete infrastructure adapters.

The Container holds the assembled object graph for a single CLI invocation.
Presentation commands receive a Container instance rather than importing
feature-level factories, keeping the adapter choice fully behind the boundary.
"""

from dataclasses import dataclass

from devworkwire.application.ports import WorkItemProvider
from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.features.work_items.application.import_service import ImportService
from devworkwire.features.work_items.application.ports import StateRepository
from devworkwire.infrastructure.external.jira.settings import JiraSettings
from devworkwire.infrastructure.external.jira.work_item_provider import (
    JiraWorkItemProvider,
)
from devworkwire.infrastructure.local.sqlite_state_store import SqliteStateStore


@dataclass(frozen=True)
class Composition:
    """Immutable holder for the provider port for one app lifecycle."""

    work_item_provider: WorkItemProvider
    state_repository: StateRepository
    import_service: ImportService


def build_composition(
    settings: JiraSettings, project_config: ProjectConfig
) -> Composition:
    """Assemble the object graph from validated settings and project config.

    The caller owns loading and validating ``JiraSettings`` and
    ``ProjectConfig``. This function only performs the wiring — no config
    parsing, no singletons.

    Raises:
        BusinessRuleViolationException: If the configured provider has no
            adapter implementation.
    """
    if project_config.provider == "jira":
        provider: WorkItemProvider = JiraWorkItemProvider(settings, project_config)
    else:
        raise BusinessRuleViolationException(
            f"Unsupported provider: {project_config.provider}",
            details="No adapter is registered for this provider.",
        )

    state_repo = SqliteStateStore()
    import_svc = ImportService(provider=provider, state_repo=state_repo)

    return Composition(
        work_item_provider=provider,
        state_repository=state_repo,
        import_service=import_svc,
    )


# Module-level singleton for the composition.
_composition: Composition | None = None


def get_composition() -> Composition:
    """Return the lazily-built composition root."""
    global _composition  # noqa: PLW0603
    if _composition is None:
        from devworkwire.presentation.cli import _build_composition

        _composition = _build_composition()
    return _composition


def get_import_service() -> ImportService:
    """Shortcut for presentation commands that only need the import service."""
    return get_composition().import_service
