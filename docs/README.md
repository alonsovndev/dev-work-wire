# DevWorkWire Documentation

Welcome to the DevWorkWire documentation. Pick your path:

## For New Users

| Guide | Description |
|-------|-------------|
| [Installation](getting-started/installation.md) | Prerequisites, clone, install, verify |
| [Configuration](getting-started/configuration.md) | `.env` variables, YAML config, Jira API token |
| [CLI Reference](guides/cli-reference.md) | All commands, interactive menu, scripting examples |
| [AI Agent Skill](guides/ai-agent-skill.md) | Use the CLI from a terminal-capable AI tool |
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
├── docs/                  # This documentation
├── scripts/               # Helper scripts (run-cli)
├── src/devworkwire/       # Application source — see architecture/overview.md
└── tests/                 # Unit and integration tests, mirrored per source module
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| CLI | Typer + prompt-toolkit menu + InquirerPy prompts |
| API Client | httpx (async) |
| Config | python-dotenv + pyaml-env |
| Testing | pytest + pytest-asyncio + respx |
