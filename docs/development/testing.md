# Testing Guide

## Test Structure

Tests mirror the source directory structure:

```
tests/
├── unit/
│   ├── config/
│   │   ├── test_app_config.py       # AppConfig singleton, env selection, env-var interpolation
│   │   └── test_project_config.py   # devworkwire.yml loading and validation
│   ├── core/
│   │   └── test_composition.py      # Container builds JiraSettings from config; caches the provider
│   ├── domain/
│   │   ├── test_entities.py         # Epic / UserStory construction and validation
│   │   └── test_value_objects.py    # IssueId / Priority / StoryPoints / Label
│   ├── jira/
│   │   └── test_jira_provider.py    # JiraProvider against respx-mocked HTTP (incl. retry/timeout/api_version wiring)
│   ├── presentation/
│   │   └── test_interactive_menu.py # Interactive menu wiring (selection -> prompt -> action), mocked
│   └── shared/
│       └── test_log_config.py       # Structured logging formatters and context
└── integration/
    └── test_cli.py                  # Typer commands end-to-end via CliRunner + respx
```

## Running Tests

```bash
# All tests
pytest

# With verbose output
pytest -v

# Specific file
pytest tests/unit/jira/test_jira_provider.py

# Specific test
pytest tests/unit/domain/test_entities.py::test_create_epic

# With coverage
pytest --cov=src
```

## Writing Tests

### Domain Tests

Domain tests are pure unit tests — no mocks, no I/O:

```python
def test_create_epic():
    epic = Epic.create(title="My Epic", description="Desc")
    assert epic.title == "My Epic"

def test_create_epic_empty_title():
    with pytest.raises(BusinessRuleViolation):
        Epic.create(title=" ", description="")
```

### Jira Adapter Tests

Use `respx` to mock HTTP responses against the real `JiraProvider`:

```python
@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-1", "fields": {"summary": "S"}})
    )
    epic = await provider.fetch_epic("PROJ-1")
    assert epic.title == "S"
```

Keep `max_retries=1` (or similarly low) in test fixtures for `JiraSettings` — `backoff`'s exponential delays otherwise slow the suite for every test that exercises a failure path.

### CLI Tests

`tests/integration/test_cli.py` invokes the Typer app through `CliRunner`, injecting a `JiraProvider` directly into the module-level `container` (bypassing real config loading):

```python
@pytest.fixture
def mock_config():
    container._jira_provider = JiraProvider(JiraSettings(..., max_retries=1))
    yield
    container._jira_provider = None
```

Cover both the success path and the error path (the CLI commands catch `Exception` and print `Error ...:` rather than raising, so assert on `result.output`, not just `exit_code`).

### Interactive Menu Tests

The interactive menu (`presentation/cli/main.py::_run_interactive_menu`) is tested by monkeypatching `InquirerPy.inquirer.select`/`.text`/`.filepath` to return canned choices, and the `_fetch_epic`/`_create_epic` helpers with `unittest.mock.AsyncMock` — this verifies menu wiring (which prompt follows which choice, which helper gets called with what argument) without needing a real terminal. End-to-end keyboard behavior is verified manually against a pty (`script -q /dev/null dwire` or similar), not in the automated suite.

## Testing Conventions

- Use `pytest` fixtures for shared setup.
- Use `pytest.mark.asyncio` for async test functions.
- Use `pytest.raises` for exception testing.
- Mock at the HTTP boundary (`respx`) or the provider/config boundary — never mock domain objects.
- Each test asserts one behavior.
