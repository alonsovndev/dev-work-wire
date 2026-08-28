# Changelog

All notable changes to DevWorkWire are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Import engine (S3)**: validate → preview → commit workflow for loading
  markdown-defined epics into project trackers.
- `ImportService` application service: orchestrates parsing, validation,
  deduplication (SHA-256 source hash), and commit with state persistence.
- `StateRepository` port and `SqliteStateStore` adapter: SQLite-backed local
  state tracking imports and work-item references (source_hash column for
  deduplication).
- `ImportPreview`, `EpicPreview`, `StoryPreview`, `ValidationReport` domain
  models for structured import data.
- `ImportRecord`, `WorkItemRef` domain models for import state tracking.
- `ImportPreviewDto`, `ImportCommitResultDto`, `WorkItemResultDto` DTOs for
  the import feature boundary.
- `dwire import preview <file>` CLI command: parse, validate, and persist a
  preview JSON for later commit.
- `dwire import commit` CLI command: execute the import from a persisted
  preview, creating epics and stories via the provider.
- `dwire import status` CLI command: list all completed imports from local state.
- `EpicMarkdownParser.parse_structured()`: two-pass parser returning
  `EpicPreview` with stories and acceptance criteria; backward-compatible
  `parse()` method preserved.
- `WorkItemProvider` extensions: `find_epic_by_key()`, `create_user_story()`,
  `update_epic()` added to the ABC and Jira adapter.
- Parser and import service test suites (19 tests across 3 test files).

### Changed

- `Composition` dataclass now holds `work_item_provider`, `state_repository`,
  and `import_service`; `get_import_service()` shortcut added.
- `import` subcommand group registered in CLI (preview/commit/status).

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
