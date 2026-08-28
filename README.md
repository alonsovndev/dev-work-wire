# DevWorkWire

Load an **already-defined** work structure — Epics → User Stories → Acceptance Criteria — into your project tracker (Jira first), validated, previewed, and duplicate-free. Driven by a developer through the `dwire` CLI, or by an AI agent through DevWorkWire's MCP server.

> DevWorkWire does not interpret or "refine" free-form text. Your input arrives already structured; DevWorkWire validates it, shows a preview, and writes it reliably.

## 🚀 Quick Start

### Install (recommended)

```bash
pipx install devworkwire
```

Or with pip:

```bash
pip install devworkwire
```

### From source (development)

```bash
git clone https://github.com/alonsovndev/devworkwire.git && cd devworkwire
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # editable install with dev tooling
cp .env.example .env                   # edit with your Jira credentials
dwire
```

## ✨ Features

- **Structured loading** — parse Epic/Story/Acceptance-Criteria Markdown into Jira, with validation before any write
- **Jira integration** — create and fetch issues via the REST API, with correct Epic → Story hierarchy
- **Context retrieval** — fetch an epic with its stories by key
- **Interactive CLI** — menu-driven interface with InquirerPy, or direct commands for scripting
- **Clean Architecture** — hexagonal design with a provider port, ready for future Linear/Azure DevOps adapters

## 💻 Usage

### Interactive menu

```bash
dwire
```

Three options available:

1. **Retrieve an epic** — Fetch epic details from Jira by key (e.g., `PROJ-123`)
2. **Create a new epic** — Parse a Markdown file and create the epic in Jira
3. **Exit**

### Direct commands (for scripts / CI)

```bash
# Fetch an epic by Jira key
dwire fetch-epic PROJ-123

# Create an epic from a markdown file
dwire create-epic data/EPIC-0-foundational/epic.md
```

> Full CLI reference: [CLI Reference Guide](docs/guides/cli-reference.md)

## 📝 Markdown Format

Place epics and stories under `data/EPIC-N-description/` with `epic.md` and `stories.md` files.

### Epics

```markdown
# Epic: My Feature

**Epic Title**: My Feature
**Epic Key**: EPIC-1
**Summary**: Short description of the epic
**Labels**: frontend, api
**Priority**: Must Have

---

**Epic Description:**
Detailed description here...
```

### User Stories

```markdown
# Story: User Authentication

**Story Title**: User Authentication
**Story Key**: STORY-1
**As a** visitor
**I want** to sign in securely
**So that** I can access my private dashboard
**Labels**: backend, auth
**Priority**: Should Have
**Story Points**: 5

---

**Acceptance Criteria:**

- User can sign in with email and password
- Invalid credentials return a clear error message
- Session remains active until logout
```

> Full template spec: [Markdown Format Guide](docs/guides/markdown-format.md)

## 🏗️ Architecture

```text
src/devworkwire/
├── main.py                      # Entry point
├── config/                      # YAML-based configuration
├── core/domain/                 # Shared kernel: issue abstractions, value objects, exceptions
├── features/                    # Vertical feature slices
│   ├── epic/                    # Epic slice: entity, use cases, port, Jira adapter, commands
│   └── story/                   # Story slice: entity, port, DTOs/mapper, Jira adapter
├── infrastructure/
│   └── external/jira/           # Shared Jira support (settings, datetime parsing)
├── presentation/                # Typer CLI shell + InquirerPy menus
└── shared/                      # Cross-cutting utilities
    ├── log_config.py            # Structured logger (JSON or plain text)
    └── utils/                   # Retry decorator
```

DevWorkWire follows **Clean Architecture** with **Domain-Driven Design**, organized as vertical feature slices, and is being consolidated around a single `WorkItemProvider` port so new trackers (Linear, Azure DevOps) can be added without touching the core.

> Deep dive: [Architecture Overview](docs/architecture/overview.md)

## 🛠️ Development

```bash
pytest                  # run all tests
pytest --cov            # with coverage
ruff check src tests    # lint
mypy src tests          # type-check
```

- **Style**: PEP 8, Google-style docstrings, full type hints
- **Naming**: camelCase variables, PascalCase classes

> Dev setup guide: [Development Setup](docs/development/setup.md) · Testing: [Testing Guide](docs/development/testing.md)

## 🗺️ Roadmap

Phase 1 (current): Jira provider, loading engine with validation/preview/confirm, `dwire` CLI, packaging. Next: progress write-back, MCP server for any MCP-compatible agent, then Linear/Azure DevOps adapters. See [specs/devworkwire-plan.md](specs/devworkwire-plan.md).

## 📚 Documentation

| Topic             | Link                                                         |
| ----------------- | ------------------------------------------------------------ |
| Installation      | [Installation Guide](docs/getting-started/installation.md)   |
| Configuration     | [Configuration Guide](docs/getting-started/configuration.md) |
| CLI Reference     | [CLI Reference Guide](docs/guides/cli-reference.md)          |
| Markdown Format   | [Markdown Format Guide](docs/guides/markdown-format.md)      |
| Architecture      | [Architecture Overview](docs/architecture/overview.md)       |
| Development Setup | [Development Setup](docs/development/setup.md)               |
| Testing Guide     | [Testing Guide](docs/development/testing.md)                 |
| Contributing      | [Contributing Guide](CONTRIBUTING.md)                        |

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated** — whether it's fixing a typo, improving documentation, squashing a bug, or proposing a new feature.

If you have an idea, open an issue to discuss it first, then submit a pull request. New to the codebase? The [Contributing Guide](CONTRIBUTING.md) walks you through setup, conventions, and your first contribution.

## ⚖️ License

MIT — see [LICENSE](LICENSE).
