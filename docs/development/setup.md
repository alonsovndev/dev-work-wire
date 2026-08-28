# Development Setup

## Prerequisites

Same as [installation](../getting-started/installation.md), plus:
- A code editor (VS Code recommended)
- Familiarity with Python type hints and async/await

## Project Conventions

### Code Style

- **PEP 8** — standard Python style
- **camelCase** for variables and functions
- **PascalCase** for classes
- **Full type hints** on all function signatures
- **Google-style docstrings** with Args, Returns, and Raises sections

### Naming

| What | Convention | Examples |
|------|-----------|----------|
| Classes | PascalCase | `Epic`, `UserStory`, `JiraEpicRepository` |
| Functions/methods | camelCase | `get_epic`, `find_epics_by_project` |
| Variables | camelCase | `epicId`, `storyKey`, `jiraConfig` |
| Files | snake_case | `epic.py`, `user_story.py`, `jira_repository.py` |
| Test files | test_ prefixed | `test_epic.py`, `test_priority.py` |

### Type Hints

Every function signature must include type hints:

```python
async def get_epic(self, issue_id: IssueId) -> Optional[Epic]:
    ...
```

Use `Optional[X]` instead of `X | None` for consistency with the existing codebase.

### Docstrings

Google-style, always including parameter and return descriptions:

```python
def create(cls, key: str, summary: str) -> "Epic":
    """
    Factory method to create an Epic instance.

    Args:
        key: Jira issue key (e.g., "PROJ-123")
        summary: Epic title/summary

    Returns:
        New Epic instance

    Raises:
        BusinessRuleViolationException: If required fields are missing
    """
```

## Running the App

```bash
# Interactive mode (editable install provides the `dwire` command)
dwire

# Or from a source checkout
./scripts/run-cli

# Or directly as a module
python -m devworkwire.presentation.cli
```

## Environment Switching

Set `APP_ENV` in `.env` to switch between YAML configs:

```bash
APP_ENV=local    # uses config_local.yml
APP_ENV=test     # uses config_test.yml
```

For running tests, the test config is loaded automatically by test fixtures.

## Directory Structure for New Features

When adding features, follow the existing vertical-slice structure — each feature owns its full stack:

```
src/devworkwire/
├── core/
│   └── domain/              # Shared kernel: issue abstractions, value objects, exceptions
├── features/
│   ├── epic/                # Reference feature slice
│   │   ├── application/     # Use cases, ports (ABCs), DTOs, mappers
│   │   ├── domain/          # Entities with factory methods
│   │   └── infrastructure/  # Repository implementation + dependencies.py composition root
│   ├── story/
│   └── <new-feature>/       # Copy the epic layout: domain → application → infrastructure
├── infrastructure/
│   └── external/jira/       # Cross-feature adapters support (settings, parsing)
├── presentation/            # CLI shell registering feature commands
└── shared/                  # Cross-cutting utilities (logging, retry)
```

**Rules for new features:**

1. Depend only on `core/` and `shared/` — plus other features' public API (`ports.py`, `dtos.py`, `mappers.py`) when collaboration is required.
2. Keep `domain/` framework-agnostic; no imports from `application` or `infrastructure`.
3. Register new CLI commands in `presentation/cli.py`, delegating to handlers inside the feature's own `presentation/` module.
4. Mirror the source tree in `tests/unit/features/<feature>/` and add adapter tests under `tests/integration/<feature>/`.
