# Changelog

All notable changes to DevWorkWire are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Reset to a vertical-slice baseline**, replacing the prior layered
  epic/story/work_items architecture: `Epic`/`UserStory` entities, value
  objects, and exceptions consolidated under `core/domain/`; a single
  `WorkItemProvider` port lives in `core/ports/`; the Jira adapter and CLI
  were rebuilt against it. The import engine (`ImportService`,
  `SqliteStateStore`, `dwire import preview/commit/status`) and the MCP
  server were removed pending redesign — `features/import_`,
  `features/progress`, `features/workitem`, `infrastructure/local/store`,
  and `presentation/mcp` are reserved empty packages for that future work.
  The sample `data/EPIC-*` markdown and the old product-plan spec were
  removed as part of this reset.
- `JiraProvider` now takes a single `JiraSettings` value object instead of
  four positional parameters, and actually reads `timeout`, `max_retries`,
  and `api_version` from config — previously declared in
  `config_local.yml`/`config_test.yml` but silently ignored (no explicit
  HTTP timeout, hardcoded retry count and API version).
- `Epic`/`UserStory` no longer gate construction behind a `_bypass_init`
  flag; `__init__` validates the title directly and `.create()` is a thin,
  documented convenience wrapper — direct construction is equally valid.

### Added

- `dwire config setup|add-project|set-default|remove-project|show|clear`
  stores the Jira base URL, email and API token plus a list of projects with
  one default in a user-level SQLite database
  (`~/.config/devworkwire/config.db`, mode `0600`; token in plaintext), so
  no code or file editing is needed. A root `--project KEY` option picks a
  configured project for one run. Connection values resolve as environment
  variables (incl. `.env`) > stored config; the project key as `--project` >
  stored default > `devworkwire.yml`. `project_key` in `devworkwire.yml` is
  now optional. `JIRA_PROJECT_KEY` is deliberately not read: the old
  `.env.example` shipped it unused, and honouring it would silently
  override existing `devworkwire.yml` setups.

- Interactive, keyboard-navigable CLI menu (`InquirerPy`), shown when
  `dwire` is run with no subcommand; `dwire fetch-epic`/`dwire create-epic`
  remain available for direct invocation/scripting.
- Startup banner (`presentation/cli/banner.py`): boxed `DWIRE` block-letter
  logo (`pyfiglet`, new dependency) with tagline, plus a
  "Developed by alonsovndev · v{version}" legend read from the installed
  package version.
- Tests for the composition root (`Container` builds and caches
  `JiraProvider` from config), the Jira provider's retry/timeout/api_version
  wiring, the interactive menu, and CLI error paths.

### Removed

- Unused `rate_limit`/`projects` keys from `config_local.yml`/
  `config_test.yml` (declared but never read by any code).

### Fixed

- `Paths.LOCAL_STORAGE_DIR` no longer resolves outside the project root via
  a relative `..`.

## [0.2.0] - 2026-08-26

### Added

- `WorkItemProvider` port: single provider boundary for all work-item
  operations, replacing per-feature `EpicRepository` and `StoryRepository`.
- `JiraWorkItemProvider`: merged Jira adapter implementing the unified port.
- `ProjectConfig`: loads `devworkwire.yml` with provider selection, project key,
  and field mappings (`story_points` custom field configurable via config).
- `--config` CLI option to point `dwire` at a custom `devworkwire.yml` path.
- `devworkwire.example.yml` documenting all available project config fields.
- Port-contract, config-loader, and field-mapping tests.

### Changed

- `JiraSettings` no longer carries `project_key`; project selection is now
  entirely owned by `ProjectConfig` (`devworkwire.yml`).
- Use cases (`CreateEpicFromMarkdown`, `GetEpicWithStories`) now depend on
  `WorkItemProvider` instead of separate repository ports.
- Composition root wires `WorkItemProvider` from `JiraSettings` +
  `ProjectConfig`, selecting the adapter by `provider` field.

### Removed

- `EpicRepository` and `StoryRepository` feature-level port ABCs.
- `JiraEpicRepository` and `JiraStoryRepository` (replaced by the unified
  `JiraWorkItemProvider`).
- Dead speculative methods (`get_user_story`, `create_story`,
  `update_story_status`) that never had a use case calling them.

## [0.1.0] - 2026-08-26

### Added

- Proper Python packaging: `pyproject.toml` with project metadata, runtime and dev
  dependencies, and the `dwire` console script entry point.
- Editable-install development flow (`pip install -e ".[dev]"`).

### Changed

- **Renamed the project from Story Flow Engine to DevWorkWire** (package
  `devworkwire`, CLI command `dwire`), per `specs/devworkwire-plan.md`.
- Source package moved from `src/app/` to `src/devworkwire/`; all imports updated.
- Documentation, CLI banner, and configuration files updated to the new identity.
