# Development Setup

## Prerequisites

Same as [installation](../getting-started/installation.md), plus:
- A code editor (VS Code recommended)
- Familiarity with Python type hints and async/await

## Project Conventions

### Code Style

- **PEP 8** — standard Python style
- **PascalCase** for classes
- **Full type hints** on all function signatures
- **Google-style docstrings** with Args, Returns, and Raises sections

### Naming

Standard Python (PEP 8) naming throughout — no camelCase:

| What | Convention | Examples |
|------|-----------|----------|
| Classes | PascalCase | `Epic`, `UserStory`, `JiraProvider` |
| Functions/methods/variables | snake_case | `fetch_epic`, `get_jira_provider`, `issue_key` |
| Files | snake_case | `entities.py`, `jira_provider.py` |
| Test files | test_ prefixed | `test_entities.py`, `test_jira_provider.py` |

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
def create(
    cls,
    title: str,
    description: str,
    priority: Optional[Priority] = None,
    labels: Optional[List[Label]] = None,
) -> "Epic":
    """
    Factory method to create an Epic instance.

    Args:
        title: Epic title
        description: Epic description
        priority: Optional priority
        labels: Optional labels

    Returns:
        New Epic instance

    Raises:
        BusinessRuleViolation: If the title is empty or blank
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

See [Architecture Overview](../architecture/overview.md) for the current source layout —
don't duplicate it here; it drifts. In short: shared domain concepts go in `core/domain/`,
cross-feature ports in `core/ports/`, feature-specific application/presentation code under
`features/<name>/`, and adapters under `infrastructure/`.

**Rules for new features:**

1. Depend only on `core/` and `shared/` — plus another feature's public API when
   collaboration is required.
2. Keep domain code framework-agnostic; no imports from infrastructure or presentation.
3. Register new CLI commands in `presentation/cli/main.py`.
4. Mirror the source tree under `tests/unit/` and add adapter tests under
   `tests/integration/`.
