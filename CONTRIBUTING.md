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
- [ ] New domain entities use factory methods (`create()`, not direct `__init__`)
- [ ] New value objects are `frozen=True` dataclasses
- [ ] Repository methods are declared in the `JiraRepository` interface first
- [ ] Relevant documentation is updated in `/docs`

## Code Conventions

See [Development Setup](docs/development/setup.md) for the full style guide.

Key points:
- **camelCase** for variables and functions
- **PascalCase** for classes
- **Full type hints** everywhere
- **Google-style docstrings**

## Architecture Rules

New code must follow the [Clean Architecture](docs/architecture/overview.md) layering:

1. **Domain layer** — no framework imports. Use factory methods and value objects.
2. **Application layer** — depends only on domain and repository interfaces.
3. **Infrastructure layer** — implements interfaces. Framework code lives here.
4. **Presentation layer** — CLI commands. Delegates to use cases.

Never import from an outer layer into an inner layer. For example, a domain entity must not import from infrastructure.

## Adding a New Feature

1. **Define the repository interface** in `application/interfaces/`
2. **Create domain objects** (entities, value objects, exceptions) in `domain/`
3. **Write the use case** in `application/use_cases/`
4. **Implement the repository** in `infrastructure/external/`
5. **Add CLI command** in `presentation/cli.py`
6. **Write tests** in the corresponding `tests/` directory

## Questions?

Open an issue for bugs or feature requests. For architectural discussions, reference the [Architecture Overview](docs/architecture/overview.md).
