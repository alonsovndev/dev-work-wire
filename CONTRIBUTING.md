# Contributing

Thanks for your interest in contributing to DevWorkWire!

## How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following the project conventions
4. Write/update tests for your changes
5. Ensure all tests pass: `pytest`
6. Submit a pull request

## PR Checklist

Before submitting, verify:

- [ ] Tests pass: `pytest`
- [ ] Coverage doesn't decrease: `pytest --cov=src`
- [ ] No new linting issues (follows PEP 8)
- [ ] Type hints on all new functions
- [ ] Google-style docstrings on all new public methods
- [ ] New domain entities validate required fields in `__init__` (`create()` is an optional convenience wrapper; direct construction is also valid)
- [ ] New value objects are `frozen=True` dataclasses
- [ ] New provider operations are declared on the `WorkItemProvider` port (`core/ports/`) first
- [ ] Relevant documentation is updated in `/docs`

## Code Conventions

See [Development Setup](docs/development/setup.md) for the full style guide.

Key points:
- **snake_case** for variables, functions, and files
- **PascalCase** for classes
- **Full type hints** everywhere
- **Google-style docstrings**

## Architecture Rules

New code must follow the [Clean Architecture](docs/architecture/overview.md) layering:

1. **Domain** (`core/domain/`) — no framework imports. Entities, value objects, and exceptions only.
2. **Ports** (`core/ports/`) — abstract interfaces such as `WorkItemProvider`; depend only on the domain.
3. **Infrastructure** (`infrastructure/`) — implements ports. HTTP and other framework code lives here.
4. **Presentation** (`presentation/cli/`) — Typer commands and the interactive menu. Obtain a configured provider from the composition root (`core/composition.py`); never construct adapters directly.

Feature-specific logic lives under `features/<name>/application/`.

Never import from an outer layer into an inner layer. For example, a domain entity must not import from infrastructure.

## Adding a New Feature

1. **Define the port method** on `WorkItemProvider` in `core/ports/`
2. **Create domain objects** (entities, value objects, exceptions) in `core/domain/`
3. **Write feature logic**, if any, in `features/<name>/application/`
4. **Implement the port** in `infrastructure/external/`
5. **Add the CLI command** in `presentation/cli/main.py`
6. **Write tests** under `tests/unit/` (mirroring the source tree) and `tests/integration/`

## Questions?

Open an issue for bugs or feature requests. For architectural discussions, reference the [Architecture Overview](docs/architecture/overview.md).
