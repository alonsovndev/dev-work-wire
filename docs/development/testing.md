# Testing Guide

## Test Structure

Tests mirror the source directory structure:

```
tests/
├── unit/
│   ├── core/
│   │   └── domain/
│   │       ├── value_objects/
│   │       │   ├── test_issue_id.py       # IssueId parsing and equality
│   │       │   ├── test_label.py          # Label validation
│   │       │   ├── test_label_set.py      # LabelSet operations
│   │       │   ├── test_priority.py       # Priority comparison
│   │       │   └── test_story_points.py   # StoryPoints arithmetic
│   │       └── exceptions/
│   │           └── test_exceptions.py     # Exception hierarchy
│   ├── features/
│   │   ├── epic/
│   │   │   ├── domain/
│   │   │   │   └── test_epic.py                  # Epic factory method tests
│   │   │   ├── application/
│   │   │   │   ├── test_create_epic_from_markdown.py
│   │   │   │   └── test_get_epic_with_stories.py # Use case tests
│   │   │   ├── infrastructure/
│   │   │   │   └── test_project_key_restrictions.py  # Authorization tests
│   │   │   └── presentation/
│   │   │       └── test_commands.py              # CLI command handler tests
│   │   └── story/
│   │       ├── domain/
│   │       │   └── test_user_story.py     # UserStory factory method tests
│   │       └── application/
│   │           └── test_story_mapper.py
│   └── presentation/
│       └── test_cli.py                    # Typer command registration tests
└── integration/
    ├── epic/
    │   └── test_jira_epic_repository.py   # Epic adapter with respx mocking
    └── story/
        └── test_jira_story_repository.py  # Story adapter with respx mocking
```

## Running Tests

```bash
# All tests
pytest

# With verbose output
pytest -v

# Specific directory
pytest tests/unit/features/epic/domain/

# Specific file
pytest tests/unit/features/epic/domain/test_epic.py

# Specific test
pytest tests/unit/features/epic/domain/test_epic.py::test_create_epic_with_valid_data

# With coverage
pytest --cov=src

# Coverage with HTML report
pytest --cov=src --cov-report=html
```

## Writing Tests

### Domain Tests

Domain tests are pure unit tests — no mocks, no I/O:

```python
def test_epic_creation_with_valid_data():
    epic = Epic.create(
        key="PROJ-123",
        numeric_id=10042,
        summary="User Auth",
        description="Implement OAuth2",
        status=IssueStatus.TODO,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    assert epic.key == "PROJ-123"
    assert epic.summary == "User Auth"
```

Test both success and failure paths:

```python
def test_epic_creation_rejects_empty_key():
    with pytest.raises(BusinessRuleViolationException):
        Epic.create(key="", numeric_id=1, summary="Test", ...)
```

### Application Tests

Use mock ports to test use cases without Jira — one per repository dependency:

```python
@pytest.fixture
def mock_epic_repo():
    repo = AsyncMock(spec=EpicRepository)
    repo.get_epic.return_value = sample_epic
    return repo

@pytest.fixture
def mock_story_repo():
    repo = AsyncMock(spec=StoryRepository)
    repo.get_stories_in_epic.return_value = [sample_story]
    return repo

@pytest.mark.asyncio
async def test_get_epic_with_stories(mock_epic_repo, mock_story_repo):
    use_case = GetEpicWithStories(
        epic_repository=mock_epic_repo, story_repository=mock_story_repo
    )
    result = await use_case.execute("PROJ-123")
    assert result.key == "PROJ-123"
    assert len(result.user_stories) == 1
```

### Integration Tests

Use `respx` to mock HTTP responses for the Jira client:

```python
@pytest.mark.asyncio
async def test_get_epic_from_jira(respx_mock):
    respx_mock.get("https://jira.example.com/rest/api/3/issue/PROJ-123").mock(
        return_value=httpx.Response(200, json=mock_epic_response)
    )
    repo = JiraEpicRepository(JiraSettings.from_dict(jira_config))
    epic = await repo.get_epic(IssueId.from_string("PROJ-123"))
    assert epic.key == "PROJ-123"
```

## Testing Conventions

- Use `pytest` fixtures for shared setup
- Use `pytest.mark.asyncio` for async test functions
- Use `pytest.raises` for exception testing
- Mock at the repository boundary, never mock domain objects
- Each test should assert one behavior
- Name tests as `test_<what>_<condition>_<expected>`
