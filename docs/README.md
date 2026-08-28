# DevWorkWire Documentation

Welcome to the DevWorkWire documentation. Pick your path:

## For New Users

| Guide | Description |
|-------|-------------|
| [Installation](getting-started/installation.md) | Prerequisites, clone, install, verify |
| [Configuration](getting-started/configuration.md) | `.env` variables, YAML config, Jira API token |
| [CLI Reference](guides/cli-reference.md) | All commands, interactive menu, scripting examples |
| [Markdown Format](guides/markdown-format.md) | Epic and user story template specification |

## For Developers

| Guide | Description |
|-------|-------------|
| [Architecture Overview](architecture/overview.md) | Clean Architecture, DDD patterns, layer diagrams |
| [Development Setup](development/setup.md) | Dev environment, code style, conventions |
| [Testing Guide](development/testing.md) | Test structure, running tests, mocking strategy |
| [Contributing](../CONTRIBUTING.md) | PR guidelines, checklist, how to contribute |

## Project Structure

```
devworkwire/
├── data/                  # Your epic and story markdown files
├── docs/                  # This documentation
├── scripts/               # Helper scripts (run-cli)
├── src/devworkwire/               # Application source
│   ├── config/            # AppConfig singleton + environment YAML files
│   ├── core/domain/       # Shared kernel (issue abstractions, value objects, exceptions)
│   ├── features/          # Vertical feature slices (epic, story)
│   ├── infrastructure/    # Shared adapter support (Jira settings, parsing)
│   ├── presentation/      # CLI shell (Typer commands + interactive menu)
│   └── shared/            # Cross-cutting utilities (logging, retry)
└── tests/                 # Unit and integration tests, mirrored per feature
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| CLI | Typer + Rich + InquirerPy |
| API Client | httpx (async) |
| Validation | Pydantic v2 |
| Parsing | markdown-it-py |
| Config | python-dotenv + pyaml-env |
| Testing | pytest + pytest-asyncio + respx |
